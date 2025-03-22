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
            raise ValueError(f"String não pode ter mais que {self.max_length} caracteres")

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
    def __init__(self, model_class: str, back_populates: Optional[str] = None, **kwargs):
        Relationship.__init__(self, model_class, back_populates)
        Field.__init__(self, **kwargs)
    
    def get_related_instance(self, instance):
        related_model = self.get_related_model()
        
        instance_id = getattr(instance, 'id', None)
        if instance_id is None:
            return None
        
        if self.back_populates:
            field_name = self.back_populates
            query = f"SELECT * FROM {related_model.__tablename__} WHERE {field_name}_id = %s"
            result = DB.execute_query(query, (instance_id,))
            if result:
                return related_model(**result[0])
        return None

class ForeignKey(Relationship, Field):
    def __init__(self, model_class: str, back_populates: Optional[str] = None, **kwargs):
        Relationship.__init__(self, model_class, back_populates)
        Field.__init__(self, **kwargs)
    
    def get_related_instance(self, instance):
        related_model = self.get_related_model()
        
        related_id = getattr(instance, f"{self.attribute_name}_id", None)
        if related_id is None:
            return None
            
        query = f"SELECT * FROM {related_model.__tablename__} WHERE id = %s"
        result = DB.execute_query(query, (related_id,))
        if result:
            return related_model(**result[0])
        return None

class ManyToManyField(Relationship):
    def __init__(self, model_class: str, through: Optional[str] = None, back_populates: Optional[str] = None):
        super().__init__(model_class, back_populates)
        self.through = through

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return ManyToManyManager(instance, self)

    def contribute_to_class(self, model, name):
        super().contribute_to_class(model, name)
        
        if not hasattr(model, '_m2m_fields'):
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
                '__tablename__': through_name.lower(),
                f"{self.parent_model.__name__.lower()}_id": IntegerField(),  # Campo como IntegerField
                f"{self.model_class.lower()}_id": IntegerField()             # Não use ForeignKey
            }
            )
            return through_class
    
    def get_related_instances(self, instance):
        related_model = self.get_related_model()
        through_model = self.get_through_model()
        
        instance_id = getattr(instance, 'id', None)
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
        
        instance_id = getattr(instance, 'id', None)
        related_id = getattr(related_obj, 'id', None)
        
        if instance_id is None or related_id is None:
            raise ValueError("Ambos os objetos devem ser salvos antes de criar uma relação.")
        
        parent_fk = f"{self.parent_model.__name__.lower()}_id"
        related_fk = f"{self.model_class.lower()}_id"
        
        
        existing = through_model.find_by(**{
        parent_fk: instance_id,
        related_fk: related_id
    })
        
        if not existing:
            through_obj = through_model(**{
                parent_fk: instance_id,
                related_fk: related_id
            })
            through_obj.save()
    
    def remove(self, instance, related_obj):
        through_model = self.get_through_model()
        
        instance_id = getattr(instance, 'id', None)
        related_id = getattr(related_obj, 'id', None)
        
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
        self.m2m_field.add(self.instance, related_obj)  # Chama o método original com a instância

    def remove(self, related_obj):
        self.m2m_field.remove(self.instance, related_obj)

    def get_related_instances(self):
        return self.m2m_field.get_related_instances(self.instance)

class DB:
    _connection = None
    _logger = Logger('DB')

    @classmethod
    def connect(cls, host="localhost", database="teste", user="admin", password="admin"):
        cls._logger.info(f"Conectando ao banco de dados {database} em {host}")
        cls._connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
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
            if query.strip().upper().startswith(('SELECT', 'RETURNING')):
                results = [dict(row) for row in cursor.fetchall()]
                cls._logger.debug(f"Resultados da query: {results}")
                return results
            conn.commit()
            cls._logger.debug(f"Query executada com sucesso, {cursor.rowcount} linhas afetadas")
            return cursor.rowcount
    
    @classmethod
    def create_tables(cls, models):
        conn = cls.get_connection()
        with conn.cursor() as cursor:
            for model in models:
                cls._create_table_for_model(cursor, model)
            
            for model in models:
                if hasattr(model, '_m2m_fields'):
                    for field_name, field in model._m2m_fields.items():
                        cls._create_m2m_table(cursor, model, field)
        
        conn.commit()
    
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
            return
        
        model_name = model.__name__.lower()
        related_model_name = m2m_field.model_class.lower()
        table_name = f"{model_name}_{related_model_name}"
        
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                {model_name}_id INTEGER NOT NULL REFERENCES {model.__tablename__}(id),
                {related_model_name}_id INTEGER NOT NULL REFERENCES {m2m_field.get_related_model().__tablename__}(id),
                UNIQUE({model_name}_id, {related_model_name}_id)
            )
        """
        cursor.execute(create_table_sql)

class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name != 'BaseModel':
            fields = {}
            for key, value in attrs.items():
                if isinstance(value, Field):
                    fields[key] = value
            attrs['_fields'] = fields
            
            if '__tablename__' not in attrs:
                attrs['__tablename__'] = name.lower()
                
        return super().__new__(cls, name, bases, attrs)
    
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        
        if name != 'BaseModel':
            for key in list(cls.__dict__):  
                value = getattr(cls, key)
                if isinstance(value, Relationship):
                    value.contribute_to_class(cls, key)

class BaseModel(metaclass=ModelMeta):
    _logger = Logger('BaseModel')

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        pass


    def save(self):
        print(self._fields)
        self.validate()
        
        is_insert = not hasattr(self, 'id') or self.id is None
        
        fields = {}
        for field_name in self._fields:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                
                if isinstance(self._fields[field_name], (OneToOneField, ForeignKey)):
                    if value is not None:
                        fields[f"{field_name}_id"] = getattr(value, 'id', value)
                else:
                    fields[field_name] = value
        
        if is_insert:
            if fields:
                columns = ', '.join(fields.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                values = list(fields.values())
                
                query = f"""
                    INSERT INTO {self.__tablename__} ({columns})
                    VALUES ({placeholders})
                    RETURNING id
                """
                result = DB.execute_query(query, values)

                if result:
                    self._logger.debug(result)
                    self.id = result
        else:
            if fields:
                set_clause = ', '.join([f"{key} = %s" for key in fields.keys()])
                values = list(fields.values()) + [self.id]
                
                query = f"""
                    UPDATE {self.__tablename__}
                    SET {set_clause}
                    WHERE id = %s
                """
                DB.execute_query(query, values)
        return self

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
        conditions = ' AND '.join([f"{key} = %s" for key in kwargs.keys()])
        values = list(kwargs.values())
        query = f"SELECT * FROM {cls.__tablename__} WHERE {conditions}"
        results = DB.execute_query(query, values)
        return results
    
    def delete(self):
        if not hasattr(self, 'id') or self.id is None:
            return False
            
        query = f"DELETE FROM {self.__tablename__} WHERE id = %s"
        DB.execute_query(query, (self.id,))
        return True


class Usuario(BaseModel):
    nome = StringField(required=True)
    email = StringField(required=True, unique=True)
    senha = StringField(required=True)

class Perfil(BaseModel):
    bio = StringField()
    data_nascimento = DateField()
    usuario = OneToOneField('Usuario', back_populates='perfil')

class Categoria(BaseModel):
    nome = StringField(required=True)
    descricao = StringField()

class Produto(BaseModel):
    nome = StringField(required=True)
    preco = FloatField(required=True)
    descricao = StringField()
    categoria = ForeignKey('Categoria', back_populates='produto')
    tag = ManyToManyField('Tag', back_populates='produtos')

class Tag(BaseModel):
    nome = StringField(required=True, unique=True)
    produtos = ManyToManyField('Produto', back_populates='tag')

if __name__ == '__main__':
    # _db = DB()
    # DB.create_tables([Usuario, Perfil, Categoria, Produto, Tag])
    
    # Categoria._fields['produto'] = ManyToManyField('Produto', back_populates='categoria')
    # Produto._fields['tag'] = ManyToManyField('Tag', back_populates='produto')
    # usuario1 = Usuario(id="3", nome="Paulo", email="joao@example.com", senha="123456")
    # usuario2 = Usuario(nome="Leopoldo", email="topterm@gmail.com", senha="344324")

    # usuario1.save()
    # usuario2.save()

    # fake = Faker('pt_BR')

    # usuario = Usuario(
    #     nome=fake.name(),
    #     email=fake.email(),
    #     senha=fake.password()
    # )
    # usuario.save()

    # perfil = Perfil(
    #     bio=fake.sentence(),
    #     data_nascimento=fake.date_of_birth(),
    #     usuario=usuario  
    # )
    # perfil.save()

    # categoria = Categoria(
    #     nome=fake.word(),
    #     descricao=fake.text(max_nb_chars=200)
    # )
    # categoria.save()

    # produto = Produto(
    #     nome=fake.word(),
    #     preco=float(fake.random_number(digits=2)),  
    #     descricao=fake.text(max_nb_chars=200),
    #     categoria=categoria
    # )
    # produto.save()

    # tag = Tag(
    #     nome=fake.word()
    # )
    # tag.save()

    # produto.tag.add(tag)
    # print(produto._fields)
    # produto.save()

    # DB.create_tables([Usuario, Perfil, Categoria, Produto, Tag])
    DB.create_tables([Usuario,Perfil, Categoria, Tag, Produto])  # Tag antes de Produto    
    #Usuario._fields['perfil'] = OneToOneField('Perfil', back_populates='usuario')
    # Categoria._fields['produto'] = ManyToManyField('Produto', back_populates='categoria')
    # Produto._fields['tag'] = ManyToManyField('Tag', back_populates='produto')
    # Criando usuários e perfis (1:1)
    admin = Usuario(nome="Admin", email="admin@loja.com", senha="admin123")
    admin.save()

    admin_perfil = Perfil(
        bio="Administrador da loja virtual",
        data_nascimento=date(1985, 3, 10),
        usuario=admin
    )
    admin_perfil.save()

    informatica = Categoria(nome="Informática", descricao="Produtos de informática")
    informatica.save()

    games = Categoria(nome="Games", descricao="Jogos e consoles")
    games.save()

    notebook = Produto(
        nome="Notebook Ultimate",
        preco=5499.90,
        descricao="Notebook para jogos de alto desempenho",
        categoria=informatica
    )
    notebook.save()

    console = Produto(
        nome="Console Game Station",
        preco=3999.90,
        descricao="Console de última geração",
        categoria=games
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

    produtos_informatica = informatica.produto.get_related_instances()
    print(f"Produtos da categoria Informática:")
    for produto in produtos_informatica:
        print(f"- {produto.nome}: R${produto.preco}")
        print(f"  Tags: {', '.join([tag.nome for tag in produto.tags.get_related_instances()])}")

    produtos_gamer = tag_gamer.produto.get_related_instances()
    print(f"Produtos com a tag Gamer:")
    for produto in produtos_gamer:
        print(f"- {produto.nome} (Categoria: {produto.categoria.nome})")

