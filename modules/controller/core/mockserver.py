import socket
from typing import Optional, Dict, List, Any, Callable, Tuple, Type
from wsgiref.simple_server import make_server
from urllib.parse import parse_qs
import json
import re
import time
import uuid
import inspect
from abc import ABC, abstractmethod
from functools import wraps
from typing import Type, List, Optional, Any, Dict, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from modules.utils.logger import Logger
from faker import Faker
from datetime import date


class Field:
    def __init__(self, required=False, unique=False):
        self.required = required
        self.unique = unique

    def validate(self, value):
        if self.required and value is None:
            raise ValueError(f"Campo obrigatório não pode ser nulo")


class StringField(Field):
    def __init__(self, max_length=255, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length

    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"Valor deve ser uma string")
        if value is not None and len(value) > self.max_length:
            raise ValueError(
                f"String não pode ter mais que {self.max_length} caracteres"
            )


class IntegerField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, int):
            raise ValueError(f"Valor deve ser um inteiro")


class FloatField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError(f"Valor deve ser um número")


class BooleanField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"Valor deve ser booleano")


class DateField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, date):
            raise ValueError(f"Valor deve ser uma data")


class Relationship:
    def __init__(self, model_class: str, back_populates: Optional[str] = None):
        self.model_class = model_class
        self.back_populates = back_populates
        self.parent_model = None
        self.attribute_name = None

    def contribute_to_class(self, model, name):
        self.parent_model = model
        self.attribute_name = name

    def get_related_model(self):
        for subclass in BaseModel.__subclasses__():
            if subclass.__name__ == self.model_class:
                return subclass
        raise ValueError(f"Modelo {self.model_class} não encontrado")


class OneToOneField(Relationship, Field):
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


class DB:
    _connection = None
    _logger = Logger("DB")

    @classmethod
    def connect(
        cls, host="localhost", database="teste", user="admin", password="admin"
    ):
        cls._logger.info(f"Conectando ao banco de dados {database} em {host}")
        cls._connection = psycopg2.connect(
            host=host, database=database, user=user, password=password
        )
        return cls._connection

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            cls.connect()
        return cls._connection

    @classmethod
    def execute_query(cls, query, params=None):
        cls._logger.debug(f"Executando query: {query} com parâmetros: {params}")
        conn = cls.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith(("SELECT", "RETURNING")):
                results = [dict(row) for row in cursor.fetchall()]
                cls._logger.debug(f"Resultados da query: {results}")
                return results
            conn.commit()
            cls._logger.debug(
                f"Query executada com sucesso, {cursor.rowcount} linhas afetadas"
            )
            return cursor.rowcount

    @classmethod
    def create_tables(cls, models):
        conn = cls.get_connection()
        with conn.cursor() as cursor:
            for model in models:
                cls._create_table_without_fks(cursor, model)

            for model in models:
                cls._add_foreign_keys(cursor, model)

            for model in models:

                if hasattr(model, "_m2m_fields"):
                    for field_name, field in model._m2m_fields.items():
                        through_model = field.get_through_model()
                        table_name = through_model.__tablename__

                        cursor.execute(
                            """
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = %s
                            );
                        """,
                            (table_name,),
                        )

                        if not cursor.fetchone()[0]:
                            model1 = model.__name__.lower()
                            model2 = field.model_class.lower()

                            cursor.execute(
                                f"""
                                CREATE TABLE {table_name} (
                                    id SERIAL PRIMARY KEY,
                                    {model1}_id INTEGER REFERENCES {model.__tablename__}(id),
                                    {model2}_id INTEGER REFERENCES {field.get_related_model().__tablename__}(id),
                                    UNIQUE({model1}_id, {model2}_id)
                                )
                            """
                            )

            conn.commit()

    @classmethod
    def _create_table_without_fks(cls, cursor, model):
        table_name = model.__tablename__
        columns = ["id SERIAL PRIMARY KEY"]

        for field_name, field in model._fields.items():
            if isinstance(field, StringField):
                columns.append(f"{field_name} VARCHAR({field.max_length})")
            elif isinstance(field, IntegerField):
                columns.append(f"{field_name} INTEGER")
            elif isinstance(field, FloatField):
                columns.append(f"{field_name} REAL")
            elif isinstance(field, BooleanField):
                columns.append(f"{field_name} BOOLEAN")
            elif isinstance(field, DateField):
                columns.append(f"{field_name} DATE")
            elif isinstance(field, (OneToOneField, ForeignKey)):
                columns.append(
                    f"{field_name}_id INTEGER"
                )

        create_table_sql = (
            f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        )
        cursor.execute(create_table_sql)

    @classmethod
    def _add_foreign_keys(cls, cursor, model):
        table_name = model.__tablename__
        foreign_keys = []

        for field_name, field in model._fields.items():
            if isinstance(field, (OneToOneField, ForeignKey)):
                related_model = field.get_related_model()
                foreign_keys.append(
                    f"ALTER TABLE {table_name} ADD FOREIGN KEY ({field_name}_id) REFERENCES {related_model.__tablename__}(id)"
                )

        for fk_sql in foreign_keys:
            cursor.execute(fk_sql)

    @classmethod
    def _create_table_for_model(cls, cursor, model):
        table_name = model.__tablename__

        columns = []
        foreign_keys = []

        columns.append("id SERIAL PRIMARY KEY")

        for field_name, field in model._fields.items():
            if isinstance(field, StringField):
                columns.append(f"{field_name} VARCHAR({field.max_length})")
            elif isinstance(field, IntegerField):
                columns.append(f"{field_name} INTEGER")
            elif isinstance(field, FloatField):
                columns.append(f"{field_name} REAL")
            elif isinstance(field, BooleanField):
                columns.append(f"{field_name} BOOLEAN")
            elif isinstance(field, DateField):
                columns.append(f"{field_name} DATE")
            elif isinstance(field, (OneToOneField, ForeignKey)):
                columns.append(f"{field_name}_id INTEGER")
                related_model = field.get_related_model()
                foreign_keys.append(
                    f"FOREIGN KEY ({field_name}_id) REFERENCES {related_model.__tablename__}(id)"
                )

        all_columns = columns + foreign_keys

        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(all_columns)}
            )
        """
        print(create_table_sql)
        cursor.execute(create_table_sql)

    @classmethod
    def _create_m2m_table(cls, cursor, model, m2m_field):
        through_model = m2m_field.get_through_model()

        if m2m_field.through:
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """
            cursor.execute(table_exists_query, (through_model.__tablename__,))
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                cls._create_table_for_model(cursor, through_model)
            return


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name != "BaseModel":
            fields = {}
            for key, value in attrs.items():
                if isinstance(value, Field):
                    fields[key] = value
            attrs["_fields"] = fields

            if "__tablename__" not in attrs:
                attrs["__tablename__"] = name.lower()

        new_class = super().__new__(cls, name, bases, attrs)

        if name != "BaseModel":
            for key in list(new_class.__dict__):
                value = getattr(new_class, key)
                if isinstance(value, Relationship):
                    value.contribute_to_class(new_class, key)

        return new_class

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)


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

                if result and result > 0:
                    self.id = result
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

    @classmethod
    def _ensure_related_fields(cls):
        for field_name, field in cls._fields.items():
            if (
                isinstance(field, (OneToOneField, ForeignKey, ManyToManyField))
                and field.back_populates
            ):
                related_model = field.get_related_model()
                if field.back_populates not in related_model._fields:
                    if isinstance(field, OneToOneField):
                        related_model._fields[field.back_populates] = OneToOneField(
                            cls.__name__, back_populates=field_name
                        )
                    elif isinstance(field, ForeignKey):
                        related_model._fields[field.back_populates] = ManyToManyField(
                            cls.__name__, back_populates=field_name
                        )
                    elif isinstance(field, ManyToManyField):
                        related_model._fields[field.back_populates] = ManyToManyField(
                            cls.__name__, back_populates=field_name
                        )

    def _update_reverse_relations(self):
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

    def validate(self):
        for field_name, field in self._fields.items():
            value = getattr(self, field_name, None)
            if not isinstance(field, Relationship):
                field.validate(value)

    @classmethod
    def find_by_id(cls, id):
        query = f"SELECT * FROM {cls.__tablename__} WHERE id = %s"
        results = DB.execute_query(query, (id,))
        if results:
            return cls(**results[0])
        return None

    @classmethod
    def find_all(cls):

        query = f"SELECT * FROM {cls.__tablename__}"
        results = DB.execute_query(query)
        return [cls(**row) for row in results]

    @classmethod
    def find_by(cls, **kwargs):
        if not kwargs:
            return []

        conditions = " AND ".join([f"{key} = %s" for key in kwargs.keys()])
        values = list(kwargs.values())
        query = f"SELECT * FROM {cls.__tablename__} WHERE {conditions}"
        results = DB.execute_query(query, values)
        return [cls(**row) for row in results]

    def delete(self):
        if not hasattr(self, "id") or self.id is None:
            return False

        query = f"DELETE FROM {self.__tablename__} WHERE id = %s"
        DB.execute_query(query, (self.id,))
        return True


class Usuario(BaseModel):
    nome = StringField(required=True)
    email = StringField(required=True, unique=True)
    senha = StringField(required=True)
    perfil = OneToOneField("Perfil", back_populates="usuario")


class Perfil(BaseModel):
    bio = StringField()
    data_nascimento = DateField()
    usuario = ForeignKey("Usuario", unique=True, back_populates="perfil")


class Categoria(BaseModel):
    nome = StringField(required=True)
    descricao = StringField()
    produtos = ManyToManyField("Produto", back_populates="categoria")


class Produto(BaseModel):
    nome = StringField(required=True)
    preco = FloatField(required=True)
    descricao = StringField()
    categoria = ForeignKey("Categoria", back_populates="produtos")
    tag = ManyToManyField("Tag", back_populates="produtos")


class Tag(BaseModel):
    nome = StringField(required=True, unique=True)
    produtos = ManyToManyField(
        "Produto", back_populates="tag"
    ) 


if __name__ == "__main__":
    # DB.create_tables([Usuario, Perfil, Categoria, Produto, Tag])
    DB.create_tables([Usuario, Perfil, Categoria, Tag, Produto])  # Tag antes de Produto
    # Usuario._fields['perfil'] = OneToOneField('Perfil', back_populates='usuario')
    # Categoria._fields['produto'] = ManyToManyField('Produto', back_populates='categoria')
    # Produto._fields['tag'] = ManyToManyField('Tag', back_populates='produto')
    # Criando usuários e perfis (1:1)
    admin = Usuario(nome="Admin", email="admin@loja.com", senha="admin123")
    admin.save()

    admin_perfil = Perfil(
        bio="Administrador da loja virtual",
        data_nascimento=date(1985, 3, 10),
        usuario=admin,
    )
    admin_perfil.save()

    admin._perfil_cache = admin_perfil
    print(f"Perfil do administrador: {admin.perfil.bio}")
    print(f"Email do usuário do perfil: {admin_perfil.usuario.email}")

    informatica = Categoria(nome="Informática", descricao="Produtos de informática")
    informatica.save()

    games = Categoria(nome="Games", descricao="Jogos e consoles")
    games.save()

    notebook = Produto(
        nome="Notebook Ultimate",
        preco=5499.90,
        descricao="Notebook para jogos de alto desempenho",
        categoria=informatica,
    )
    notebook.save()

    console = Produto(
        nome="Console Game Station",
        preco=3999.90,
        descricao="Console de última geração",
        categoria=games,
    )
    console.save()

    tag_gamer = Tag(nome="Gamer")
    tag_gamer.save()

    tag_premium = Tag(nome="Premium")
    tag_premium.save()

    tag_oferta = Tag(nome="Oferta da Semana")
    tag_oferta.save()

    notebook.tag.add(tag_gamer)
    notebook.tag.add(tag_premium)
    console.tag.add(tag_gamer)
    console.tag.add(tag_oferta)

    print(f"Perfil do administrador: {admin.perfil.bio}")
    print(f"Email do usuário do perfil: {admin_perfil.usuario.email}")
    informatica.produtos.add(notebook)
    produtos_informatica = informatica.produtos.get_related_instances()
    print(f"Produtos da categoria Informática:")
    for produto in produtos_informatica:
        print(f"- {produto.nome}: R${produto.preco}")
        print(
            f"  Tags: {', '.join([tag.nome for tag in produto.tag.get_related_instances()])}"
        )

    produtos_gamer = tag_gamer.produtos.get_related_instances()
    print(f"Produtos com a tag Gamer:")
    for produto in produtos_gamer:
        print(f"- {produto.nome} (Categoria: {produto.categoria.nome})")

class Request:
    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get('REQUEST_METHOD', 'GET')
        self.path = environ.get('PATH_INFO', '/')
        self.query_params = parse_qs(environ.get('QUERY_STRING', ''))
        self.url_params = {}
        self.session = None
        self.user = None
        
        self.body = None
        if self.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                content_type = environ.get('CONTENT_TYPE', '')
                
                if content_length > 0:
                    body = environ['wsgi.input'].read(content_length)
                    
                    if 'application/json' in content_type:
                        self.body = json.loads(body)
                    elif 'application/x-www-form-urlencoded' in content_type:
                        self.body = parse_qs(body.decode('utf-8'))
                    else:
                        self.body = body.decode('utf-8')
            except Exception:
                self.body = None

    def get_form_value(self, field_name: str, default=None) -> Any:
        if self.body is None:
            return default
        
        if isinstance(self.body, dict):
            if field_name in self.body:
                return self.body.get(field_name, default)
        
        elif isinstance(self.body, dict) and field_name in self.body:
            values = self.body.get(field_name)
            if isinstance(values, list) and values:
                return values[0]
            return values
        
        return default

class Response:
    """Representa uma resposta HTTP."""
    def __init__(self, status: str = "200 OK", body: str = "", 
                 headers: List[tuple] = None, content_type: str = "text/html"):
        self.status = status
        self.body = body
        
        if headers is None:
            headers = []

        self.headers = [('Content-Type', content_type)]
        for header in headers:
            self.headers.append(header)
        
    def add_header(self, name: str, value: str):
        """Adiciona um cabeçalho à resposta."""
        self.headers.append((name, value))
        
    @classmethod
    def json(cls, data: Any, status: str = "200 OK"):
        """Cria uma resposta JSON."""
        return cls(
            status=status,
            body=json.dumps(data),
            content_type="application/json"
        )
        
    @classmethod
    def html(cls, content: str, status: str = "200 OK"):
        """Cria uma resposta HTML."""
        return cls(
            status=status,
            body=content,
            content_type="text/html"
        )
        
    @classmethod
    def text(cls, content: str, status: str = "200 OK"):
        """Cria uma resposta de texto simples."""
        return cls(
            status=status,
            body=content,
            content_type="text/plain"
        )
        
    @classmethod
    def redirect(cls, location: str, status: str = "302 Found"):
        """Cria uma resposta de redirecionamento."""
        return cls(
            status=status,
            headers=[('Location', location)],
            body=""
        )

# Definição de códigos de status HTTP
Response.status_messages = {
    200: "OK",
    201: "Created",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error"
}

class ResponseFactory:
    """Fábrica para criar diferentes tipos de respostas."""
    
    @staticmethod
    def create_response(status_code: int, body: Any = None, 
                        headers: Dict[str, str] = None) -> Response:
        """Cria uma resposta baseada no código de status e corpo."""
        status = f"{status_code} {Response.status_messages.get(status_code, 'Unknown')}"
        
        if isinstance(body, dict) or isinstance(body, list):
            return Response.json(body, status)
        elif isinstance(body, str):
            return Response.html(body, status)
        else:
            return Response(status=status)
    
    @staticmethod
    def create_error_response(status_code: int, message: str) -> Response:
        """Cria uma resposta de erro."""
        return Response.json({"error": message}, 
                             f"{status_code} {Response.status_messages.get(status_code, 'Error')}")


# Padrão Singleton para sessões
class SessionManager:

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance.sessions = {}
            cls._instance.session_timeout = 1800  # 30 minutos
        return cls._instance
    
    def create_session(self, user_data: Dict[str, Any] = None) -> str:
        """Cria uma nova sessão."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'data': user_data or {},
            'created_at': time.time(),
            'last_access': time.time()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtém dados de uma sessão."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Verifica se a sessão expirou
            if time.time() - session['last_access'] > self.session_timeout:
                self.destroy_session(session_id)
                return None
            
            # Atualiza o último acesso
            session['last_access'] = time.time()
            return session['data']
        
        return None
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Atualiza dados de uma sessão."""
        if session_id in self.sessions:
            self.sessions[session_id]['data'].update(data)
            self.sessions[session_id]['last_access'] = time.time()
            return True
        return False
    
    def destroy_session(self, session_id: str) -> bool:
        """Destrói uma sessão."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove sessões expiradas."""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session['last_access'] > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            self.destroy_session(session_id)

# Nova implementação: Sistema de Autenticação
class AuthManager:
    """Gerencia autenticação e autorização de usuários."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthManager, cls).__new__(cls)
            cls._instance.users = {}
            cls._instance.roles = {}
        return cls._instance
    
    def register_user(self, username: str, password: str, roles: List[str] = None):
        """Registra um novo usuário."""
        # Em produção, a senha deve ser armazenada com hash e salt
        self.users[username] = {
            'password': password,
            'roles': roles or []
        }
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Autentica um usuário."""
        if username in self.users and self.users[username]['password'] == password:
            user_data = {
                'username': username,
                'roles': self.users[username]['roles']
            }
            return user_data
        return None
    
    def has_role(self, user_data: Dict[str, Any], role: str) -> bool:
        """Verifica se um usuário tem um determinado papel."""
        if user_data and 'roles' in user_data:
            return role in user_data['roles']
        return False


# Nova implementação: Middleware de Sessão
class SessionMiddleware:
    """Middleware para gerenciar sessões."""
    def __init__(self, cookie_name='session_id'):
        self.session_manager = SessionManager()
        self.cookie_name = cookie_name
    
    def process_request(self, request: Request):
        """Processa a requisição, carregando dados da sessão."""
        # Verifica se há um cookie de sessão
        cookies = {}
        cookie_header = request.environ.get('HTTP_COOKIE', '')
        # Set the request.user from the session data
        if request.session is not None:
            request.user = request.session.get('user')

        for cookie in cookie_header.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                cookies[name] = value
        
        session_id = cookies.get(self.cookie_name)
        if session_id:
            request.session = self.session_manager.get_session(session_id)
            # Set the request.user from the session data
            if request.session is not None:
                request.user = request.session.get('user')
            print(request.session)
        
        return request
    
    def process_response(self, request: Request, response: Response) -> Response:
        """Processa a resposta, atualizando cookies de sessão se necessário."""
        if request.session:
            cookies = {}
            cookie_header = request.environ.get('HTTP_COOKIE', '')
            
            for cookie in cookie_header.split(';'):
                if '=' in cookie.strip():
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
            
            if self.cookie_name not in cookies:
                for session_id, session_data in self.session_manager.sessions.items():
                    if session_data.get('data') == request.session:
                        response.add_header('Set-Cookie', f"{self.cookie_name}={session_id}; Path=/; HttpOnly")
                        break
        
        return response

def require_auth(role: str = None):
    """Decorator para requerer autenticação e autorização."""
    def decorator(handler):
        @wraps(handler)
        def wrapper(request, *args, **kwargs):
            if not request.user:
                return Response.redirect('/login')
            
            if role and not AuthManager().has_role(request.user, role):
                return ResponseFactory.create_error_response(403, "Permissão negada")
            
            return handler(request, *args, **kwargs)
        return wrapper
    return decorator


class Field:
    """Base para campos de formulário."""
    
    def __init__(self, required=True, label=None, validators=None):
        self.required = required
        self.label = label
        self.validators = validators or []
        self.name = None
        self.value = None
        self.errors = []
    
    def validate(self, value):
        """Valida o valor do campo."""
        self.value = value
        self.errors = []
        
        if self.required and (value is None or value == ''):
            self.errors.append(f"O campo {self.name} é obrigatório")
            return False
        
        for validator in self.validators:
            result = validator(value)
            if isinstance(result, str): 
                self.errors.append(result)
        
        return len(self.errors) == 0


class StringField(Field):
    def __init__(self, min_length=None, max_length=None, **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value):
        """Valida o valor do campo."""
        if not super().validate(value):
            return False
        
        if value is not None and value != '':
            if self.min_length and len(value) < self.min_length:
                self.errors.append(f"O campo {self.name} deve ter pelo menos {self.min_length} caracteres")
            
            if self.max_length and len(value) > self.max_length:
                self.errors.append(f"O campo {self.name} deve ter no máximo {self.max_length} caracteres")
        
        return len(self.errors) == 0

class EmailField(StringField):
    """Campo de email."""
    
    def validate(self, value):
        """Valida se o valor é um email válido."""
        if not super().validate(value):
            return False
        
        if value and not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', value):
            self.errors.append(f"O campo {self.name} deve ser um email válido")
        
        return len(self.errors) == 0

class IntegerField(Field):
    def __init__(self, min_value=None, max_value=None, **kwargs):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value):
        if not super().validate(value):
            return False
        
        try:
            if value is not None and value != '':
                int_value = int(value)
                
                if self.min_value is not None and int_value < self.min_value:
                    self.errors.append(f"O campo {self.name} deve ser maior ou igual a {self.min_value}")
                
                if self.max_value is not None and int_value > self.max_value:
                    self.errors.append(f"O campo {self.name} deve ser menor ou igual a {self.max_value}")
        except ValueError:
            self.errors.append(f"O campo {self.name} deve ser um número inteiro")
        
        return len(self.errors) == 0

class Form:
    """Base para definição de formulários."""
    
    def __init__(self, data=None):
        self.data = data or {}
        self.errors = {}
        
        # Atribui nomes aos campos com base nos atributos da classe
        for name, field in self._get_fields():
            field.name = name
    
    def _get_fields(self):
        """Obtém todos os campos do formulário."""
        fields = []
        for name, field in inspect.getmembers(self.__class__):
            if isinstance(field, Field):
                fields.append((name, field))
        return fields
    
    def validate(self):
        """Valida todos os campos do formulário."""
        is_valid = True
        
        for name, field in self._get_fields():
            value = self.data.get(name)
            if not field.validate(value):
                self.errors[name] = field.errors
                is_valid = False
        
        return is_valid

class Controller:
    """Classe base para controladores."""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.session_manager = SessionManager()
    
    def get_current_user(self, request: Request):
        """Obtém o usuário atual da requisição."""
        if request.session and 'user' in request.session:
            return request.session['user']
        return None
    
    def login_user(self, request: Request, username: str, password: str) -> bool:
        """Autentica um usuário e inicia uma sessão."""
        user_data = self.auth_manager.authenticate(username, password)
        if user_data:
            # Extrai o cookie de sessão corretamente
            cookies = {}
            cookie_header = request.environ.get('HTTP_COOKIE', '')
            
            for cookie in cookie_header.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
            
            session_id = cookies.get('session_id')
            
            # Cria ou atualiza a sessão
            if session_id and self.session_manager.get_session(session_id):
                self.session_manager.update_session(session_id, {'user': user_data})
            else:
                session_id = self.session_manager.create_session({'user': user_data})
            
            return True
        return False

    # Corrigir o método logout_user no Controller
    def logout_user(self, request: Request) -> bool:
        """Encerra a sessão do usuário."""
        # Extrai o cookie de sessão corretamente
        cookies = {}
        cookie_header = request.environ.get('HTTP_COOKIE', '')
        
        for cookie in cookie_header.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                cookies[name] = value
        
        session_id = cookies.get('session_id')
        
        if session_id:
            return self.session_manager.destroy_session(session_id)
        return False



# Nova implementação: Integração com Modelo
class Model(ABC):
    """Classe base para modelos de dados."""
    
    @abstractmethod
    def save(self):
        """Salva o modelo."""
        pass
    
    @abstractmethod
    def delete(self):
        """Exclui o modelo."""
        pass
    
    @classmethod
    @abstractmethod
    def get(cls, id):
        """Obtém um modelo pelo ID."""
        pass
    
    @classmethod
    @abstractmethod
    def all(cls):
        """Obtém todos os modelos."""
        pass


class Router:
    """Gerencia o roteamento de requisições para controladores."""
    
    def __init__(self):
        self.routes = []
        self.middlewares = []
    
    def register_routes(self, routes: Dict[str, Dict[str, Callable]]):
        """Registra rotas no formato {path: {method: handler}}."""
        for path, methods in routes.items():
            for method, handler in methods.items():
                self.add_route(path, method.upper(), handler)
    
    def add_route(self, path: str, method: str, handler: Callable):
        """Adiciona uma rota ao roteador."""
        # Converte caminhos como "/users/{id}" para expressões regulares
        pattern = re.sub(r'{([^/]+)}', r'(?P<\1>[^/]+)', path)
        regex = re.compile(f'^{pattern}$')
        self.routes.append((regex, method, handler))
    
    def add_middleware(self, middleware):
        """Adiciona um middleware ao roteador."""
        self.middlewares.append(middleware)
    
    def dispatch(self, request: Request) -> Response:
        """Despacha a requisição para o handler apropriado."""
        # Aplica middlewares na requisição
        for middleware in self.middlewares:
            if hasattr(middleware, 'process_request'):
                request = middleware.process_request(request)
        
        # Encontra handler correspondente
        for regex, method, handler in self.routes:
            match = regex.match(request.path)
            if match and request.method == method:
                # Extrai parâmetros da URL
                url_params = match.groupdict()
                request.url_params = url_params
                
                try:
                    response = handler(request)
                except Exception as e:
                    response = ResponseFactory.create_error_response(500, str(e))
                
                # Aplica middlewares na resposta
                for middleware in reversed(self.middlewares):
                    if hasattr(middleware, 'process_response'):
                        response = middleware.process_response(request, response)
                
                return response
        
        # Rota não encontrada
        return ResponseFactory.create_error_response(404, "Not Found")


class Server:
    """Servidor HTTP que gerencia o ciclo de vida da aplicação."""
    
    def __init__(self, host: str = 'localhost', port: int = 8000):
        self.host = host
        self.port = port
        self.router = Router()
        self.running = False
        
        # Adiciona middleware de sessão por padrão
        self.router.add_middleware(SessionMiddleware())
    
    def start(self):
        """Inicia o servidor."""
        self.running = True
        server = make_server(self.host, self.port, self.application)
        print(f"Servidor iniciado em http://{self.host}:{self.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Servidor encerrado")
        
    def application(self, environ, start_response):
        """Função WSGI para processar requisições."""
        request = Request(environ)
        response = self.router.dispatch(request)
        start_response(response.status, response.headers)
        return [response.body.encode('utf-8')]
        
    def register_routes(self, routes):
        """Registra rotas no roteador."""
        self.router.register_routes(routes)
    
    def add_middleware(self, middleware):
        """Adiciona um middleware ao servidor."""
        self.router.add_middleware(middleware)


# Exemplo de uso
def example_usage():
    # Cria o servidor
    server = Server(host="localhost", port=8000)
    
    # Inicializa o gerenciador de autenticação
    auth_manager = AuthManager()
    auth_manager.register_user("admin", "senha123", ["admin"])
    auth_manager.register_user("user", "user123", ["user"])
    
    # Exemplo de formulário de login
    class LoginForm(Form):
        username = StringField(required=True)
        password = StringField(required=True)
    
    # Exemplo de controlador
    class UserController(Controller):
        def login(self, request: Request) -> Response:
            if request.method == "GET":
                return Response.html("""
                <form method="post" action="/login">
                    <input type="text" name="username" placeholder="Nome de usuário"><br>
                    <input type="password" name="password" placeholder="Senha"><br>
                    <button type="submit">Entrar</button>
                </form>
                """)
            elif request.method == "POST":
                # Extrair os dados do formulário de maneira segura
                form_data = {}
                if request.body:
                    if isinstance(request.body, dict):
                        for key, value in request.body.items():
                            # Trata listas (comum em form-urlencoded)
                            if isinstance(value, list) and value:
                                form_data[key] = value[0]
                            else:
                                form_data[key] = value
                
                form = LoginForm(form_data)
                if form.validate():
                    username = request.get_form_value("username")[0]
                    password = request.get_form_value("password")[0]
                    print(username, password)
                    if self.login_user(request, username, password):
                        return Response.redirect("/dashboard")
                    else:
                        return Response.html("<p>Usuário ou senha inválidos.</p>")
                else:
                    return Response.html(f"<p>Erros no formulário: {form.errors}</p>")
                
        @require_auth()
        def dashboard(self, request: Request) -> Response:
            return Response.html(f"<h1>Bem-vindo ao painel, {request.user['username']}!</h1>")
        
        @require_auth(role="admin")
        def admin_area(self, request: Request) -> Response:
            return Response.html("<h1>Área do Administrador</h1>")
    
    # Instancia o controlador
    user_controller = UserController()
    
    # Registra as rotas
    routes = {
        "/": {
            "GET": lambda request: Response.html("<h1>Bem-vindo ao meu framework web!</h1>"),
        },
        "/login": {
            "GET": user_controller.login,
            "POST": user_controller.login,
        },
        "/dashboard": {
            "GET": user_controller.dashboard,
        },
        "/admin": {
            "GET": user_controller.admin_area,
        },
        "/hello": {
            "GET": lambda request: Response.text("Olá, mundo!"),
        },
        "/greet/{name}": {
            "GET": lambda request: Response.text(f"Olá, {request.url_params['name']}!"),
        },
        "/json": {
            "GET": lambda request: Response.json({"message": "Isso é um JSON!"}),
        },
    }
    
    server.register_routes(routes)
    server.start()

if __name__ == "__main__":
    example_usage()