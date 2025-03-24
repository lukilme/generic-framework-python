from modules.utils.logger import Logger

class ModelRegistry:
    _models = {}
    
    @classmethod
    def register(cls, model):
        cls._models[model.__name__] = model
    
    @classmethod
    def get_model(cls, name):
        return cls._models.get(name)
    
    @classmethod
    def get_all_models(cls):
        return list(cls._models.values())


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name != "BaseModel":
            fields = {}
            for key, value in attrs.items():
                if hasattr(value, 'validate'):  # Verificação por atributo em vez de tipo
                    fields[key] = value
            attrs["_fields"] = fields

            if "__tablename__" not in attrs:
                attrs["__tablename__"] = name.lower()

        new_class = super().__new__(cls, name, bases, attrs)

        if name != "BaseModel":
            ModelRegistry.register(new_class)
            
            for key in list(new_class.__dict__):
                value = getattr(new_class, key)
                if hasattr(value, 'contribute_to_class'):
                    value.contribute_to_class(new_class, key)

        return new_class

class BaseModel(metaclass=ModelMeta):
    _logger = Logger("BaseModel")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        if hasattr(self, "id"):
            return f"{self.__class__.__name__}(id={self.id})"
        return f"{self.__class__.__name__}(não salvo)"

    def save(self):
        self.validate()
        
        from modules.database.db import DB
        from modules.database.relationships import Relationship, OneToOneField, ForeignKey
        
        is_insert = not hasattr(self, "id") or self.id is None

        fields = {}
        for field_name, field in self._fields.items():
            if hasattr(self, field_name) and not isinstance(field, Relationship):
                value = getattr(self, field_name)
                fields[field_name] = value
            elif isinstance(field, (OneToOneField, ForeignKey)):
                related_obj = getattr(self, f"_{field_name}_cache", None)
                if related_obj is not None:
                    fields[f"{field_name}_id"] = getattr(related_obj, "id", None)
                elif hasattr(self, f"{field_name}_id"):
                    fields[f"{field_name}_id"] = getattr(self, f"{field_name}_id")

        if is_insert:
            if fields:
                columns = ", ".join(fields.keys())
                placeholders = ", ".join(["%s"] * len(fields))
                values = list(fields.values())

                query = f"""
                    INSERT INTO {self.__tablename__} ({columns})
                    VALUES ({placeholders})
                    RETURNING id
                """
                result = DB.execute_query(query, values)

                if result and len(result) > 0:
                    self.id = result[0]["id"]
        else:
            if fields:
                set_clause = ", ".join([f"{key} = %s" for key in fields.keys()])
                values = list(fields.values()) + [self.id]

                query = f"""
                    UPDATE {self.__tablename__}
                    SET {set_clause}
                    WHERE id = %s
                """
                DB.execute_query(query, values)

        self._update_reverse_relations()

        return self

    def validate(self):
        for field_name, field in self._fields.items():
            value = getattr(self, field_name, None)
            from modules.database.relationships import Relationship
            if not isinstance(field, Relationship):
                field.validate(value)

    
    def _update_reverse_relations(self):
        from modules.database.db import DB
        from modules.database.relationships import OneToOneField

        for field_name, field in self._fields.items():
            if isinstance(field, OneToOneField) and field.back_populates:
                related_obj = getattr(self, field_name, None)
                if related_obj is not None:
                    related_model = field.get_related_model()

                    if field.back_populates in related_model._fields:
                        back_field = related_model._fields[field.back_populates]

                        if isinstance(back_field, OneToOneField):
                            setattr(related_obj, f"{field.back_populates}_id", self.id)
                            setattr(related_obj, f"_{field.back_populates}_cache", self)

                            if (
                                hasattr(related_obj, "id")
                                and related_obj.id is not None
                            ):
                                query = f"""
                                    UPDATE {related_model.__tablename__}
                                    SET {field.back_populates}_id = %s
                                    WHERE id = %s
                                """
                                DB.execute_query(query, (self.id, related_obj.id))
    
    @classmethod
    def find_by_id(cls, id):
        from modules.database.db import DB
        
        query = f"SELECT * FROM {cls.__tablename__} WHERE id = %s"
        results = DB.execute_query(query, (id,))
        if results and len(results) > 0:
            return cls(**results[0])
        return None

    @classmethod
    def find_all(cls):
        from modules.database.db import DB
        
        query = f"SELECT * FROM {cls.__tablename__}"
        results = DB.execute_query(query)
        return [cls(**row) for row in results]

    @classmethod
    def find_by(cls, **kwargs):
        from modules.database.db import DB
        
        if not kwargs:
            return []

        conditions = " AND ".join([f"{key} = %s" for key in kwargs.keys()])
        values = list(kwargs.values())
        query = f"SELECT * FROM {cls.__tablename__} WHERE {conditions}"
        results = DB.execute_query(query, values)
        return [cls(**row) for row in results]

    def delete(self):
        from modules.database.db import DB
        
        if not hasattr(self, "id") or self.id is None:
            return False

        query = f"DELETE FROM {self.__tablename__} WHERE id = %s"
        DB.execute_query(query, (self.id,))
        return True