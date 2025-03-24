from abc import ABC, abstractmethod
from modules.database.fields import Field
from typing import Type, List, Any, Optional, Dict, Union


class AbstractRelationship(ABC):
    def __init__(self, model_class, back_populates=None):
        self.model_class = model_class
        self.back_populates = back_populates
        self.parent_model = None
        self.attribute_name = None
    
    def contribute_to_class(self, model, name):
        self.parent_model = model
        self.attribute_name = name
    
    def get_related_model(self):
        # Importação tardia para evitar circular import
        from modules.database.registry import ModelRegistry
        return ModelRegistry.get_model(self.model_class)

class Relationship(AbstractRelationship, Field):
    def __init__(self, model_class, back_populates=None, **kwargs):
        AbstractRelationship.__init__(self, model_class, back_populates)
        Field.__init__(self, **kwargs)
    
    def get_sql_definition(self):
        return "INTEGER"  # Para o ID da chave estrangeira

class OneToOneField(Relationship):
    def __init__(self, model_class, back_populates=None, **kwargs):
        super().__init__(model_class, back_populates, **kwargs)
    
    def __get__(self, instance, owner):
        if instance is None:
            return self

        cache_name = f"_{self.attribute_name}_cache"
        if hasattr(instance, cache_name):
            return getattr(instance, cache_name)

        related_instance = self.get_related_instance(instance)
        setattr(instance, cache_name, related_instance)
        return related_instance

    def __set__(self, instance, value):
        cache_name = f"_{self.attribute_name}_cache"
        setattr(instance, cache_name, value)

        if value is not None and self.back_populates:
            related_field = getattr(self.get_related_model(), self.back_populates, None)
            if related_field and isinstance(related_field, OneToOneField):
                setattr(value, f"_{related_field.attribute_name}_cache", instance)

    def get_related_instance(self, instance):
        # Importação tardia
        from modules.database.db import DB
        
        related_model = self.get_related_model()

        instance_id = getattr(instance, "id", None)
        if instance_id is None:
            return None

        fk_field = f"{self.attribute_name}_id"
        if hasattr(instance, fk_field):
            related_id = getattr(instance, fk_field)
            if related_id:
                query = f"SELECT * FROM {related_model.__tablename__} WHERE id = %s"
                result = DB.execute_query(query, (related_id,))
                if result and len(result) > 0:
                    return related_model(**result[0])

        if self.back_populates:
            related_fk = f"{self.back_populates}_id"
            query = (
                f"SELECT * FROM {related_model.__tablename__} WHERE {related_fk} = %s"
            )
            result = DB.execute_query(query, (instance_id,))
            if result and len(result) > 0:
                return related_model(**result[0])

        return None


class ForeignKey(Relationship, Field):
    def __init__(
        self, model_class: str, back_populates: Optional[str] = None, **kwargs
    ):
        Relationship.__init__(self, model_class, back_populates)
        Field.__init__(self, **kwargs)

    def __get__(self, instance, owner):
        if instance is None:
            return self

        cache_name = f"_{self.attribute_name}_cache"
        if hasattr(instance, cache_name):
            cached_value = getattr(instance, cache_name)
            if cached_value is not None:
                return cached_value

        related_instance = self.get_related_instance(instance)

        setattr(instance, cache_name, related_instance)

        return related_instance

    def __set__(self, instance, value):
        cache_name = f"_{self.attribute_name}_cache"
        setattr(instance, cache_name, value)

        if value is not None:
            setattr(instance, f"{self.attribute_name}_id", getattr(value, "id", value))
        else:
            setattr(instance, f"{self.attribute_name}_id", None)

        if value is not None and self.back_populates:
            related_field = getattr(self.get_related_model(), self.back_populates, None)
            if related_field and isinstance(related_field, ManyToManyField):
                pass

    def get_related_instance(self, instance):
        related_model = self.get_related_model()

        instance_id = getattr(instance, "id", None)
        if instance_id is None:
            return None

        fk_field = f"{self.attribute_name}_id"
        if hasattr(instance, fk_field):
            related_id = getattr(instance, fk_field)
            if related_id:
                query = f"SELECT * FROM {related_model.__tablename__} WHERE id = %s"
                result = DB.execute_query(query, (related_id,))
                if result and len(result) > 0:
                    return related_model(**result[0])

        if self.back_populates:
            related_fk = f"{self.back_populates}_id"
            query = f"SELECT * FROM {related_model.__tablename__} WHERE {related_fk} = %s LIMIT 1"
            result = DB.execute_query(query, (instance_id,))
            if result and len(result) > 0:
                return related_model(**result[0])

        return None


class ManyToManyField(Relationship):
    def __init__(
        self,
        model_class: str,
        through: Optional[str] = None,
        back_populates: Optional[str] = None,
    ):
        super().__init__(model_class, back_populates)
        self.through = through

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return ManyToManyManager(instance, self)

    def __iter__(self):
        return iter(self.get_related_instances())

    def contribute_to_class(self, model, name):
        super().contribute_to_class(model, name)

        if not hasattr(model, "_m2m_fields"):
            model._m2m_fields = {}
        model._m2m_fields[name] = self

    def get_through_model(self):
        if self.through:
            for subclass in BaseModel.__subclasses__():
                if subclass.__name__ == self.through:
                    return subclass
            raise ValueError(f"Modelo intermediário {self.through} não encontrado")
        else:
            models = sorted([self.parent_model.__name__, self.model_class])
            through_name = f"{models[0]}_{models[1]}"

            for subclass in BaseModel.__subclasses__():
                if subclass.__name__ == through_name:
                    return subclass

            through_class = type(
                through_name,
                (BaseModel,),
                {
                    "__tablename__": through_name.lower(),
                    f"{self.parent_model.__name__.lower()}_id": IntegerField(),
                    f"{self.model_class.lower()}_id": IntegerField(),
                },
            )
            return through_class

    def get_related_instances(self, instance):
        related_model = self.get_related_model()
        through_model = self.get_through_model()

        instance_id = getattr(instance, "id", None)
        if instance_id is None:
            return []

        parent_fk = f"{self.parent_model.__name__.lower()}_id"
        related_fk = f"{self.model_class.lower()}_id"

        query = f"""
            SELECT r.* FROM {related_model.__tablename__} r
            JOIN {through_model.__tablename__} t ON r.id = t.{related_fk}
            WHERE t.{parent_fk} = %s
        """
        results = DB.execute_query(query, (instance_id,))

        return [related_model(**row) for row in results]

    def add(self, instance, related_obj):
        through_model = self.get_through_model()

        instance_id = getattr(instance, "id", None)
        related_id = getattr(related_obj, "id", None)

        if instance_id is None or related_id is None:
            raise ValueError(
                "Ambos os objetos devem ser salvos antes de criar uma relação."
            )

        parent_fk = f"{self.parent_model.__name__.lower()}_id"
        related_fk = f"{self.model_class.lower()}_id"

        existing = through_model.find_by(
            **{parent_fk: instance_id, related_fk: related_id}
        )

        if not existing:
            through_obj = through_model(
                **{parent_fk: instance_id, related_fk: related_id}
            )
            through_obj.save()

    def remove(self, instance, related_obj):
        through_model = self.get_through_model()

        instance_id = getattr(instance, "id", None)
        related_id = getattr(related_obj, "id", None)

        if instance_id is None or related_id is None:
            return

        parent_fk = f"{self.parent_model.__name__.lower()}_id"
        related_fk = f"{self.model_class.lower()}_id"

        query = f"""
            DELETE FROM {through_model.__tablename__}
            WHERE {parent_fk} = %s AND {related_fk} = %s
        """
        DB.execute_query(query, (instance_id, related_id))


class ManyToManyManager:
    def __init__(self, instance, m2m_field):
        self.instance = instance
        self.m2m_field = m2m_field

    def add(self, related_obj):
        self.m2m_field.add(self.instance, related_obj)

    def remove(self, related_obj):
        self.m2m_field.remove(self.instance, related_obj)

    def get_related_instances(self):
        return self.m2m_field.get_related_instances(self.instance)

