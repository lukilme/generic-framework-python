from modules.utils.logger import Logger
from modules.database.connection import DatabaseConnection
from modules.database.abstract.model_register import ModelRegistry

class DB:
    _connection = None
    _logger = Logger("DB")
    
    @classmethod
    def connect(cls, host="localhost", database="teste", user="admin", password="admin"):
        cls._logger.info(f"Conectando ao banco de dados {database} em {host}")
        cls._connection = DatabaseConnection(host, database, user, password)
        return cls._connection

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            cls.connect()
        return cls._connection

    @classmethod
    def execute_query(cls, query, params=None):
        return cls.get_connection().execute_query(query, params)
    
    @classmethod
    def create_tables(cls, models):
        for model in models:
            if model.__name__ not in ModelRegistry._models:
                ModelRegistry.register(model)
        
        conn = cls.get_connection().get_connection()
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
        
        from modules.database.relationships import Relationship, OneToOneField, ForeignKey
        
        for field_name, field in model._fields.items():
            if not isinstance(field, Relationship):
                columns.append(f"{field_name} {field.get_sql_definition()}")
            elif isinstance(field, (OneToOneField, ForeignKey)):
                columns.append(f"{field_name}_id INTEGER")
        
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        cursor.execute(create_table_sql)
    
    @classmethod
    def _add_foreign_keys(cls, cursor, model):
        table_name = model.__tablename__
        foreign_keys = []
        
        from modules.database.relationships import OneToOneField, ForeignKey
        
        for field_name, field in model._fields.items():
            if isinstance(field, (OneToOneField, ForeignKey)):
                related_model = field.get_related_model()
                foreign_keys.append(
                    f"ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_{field_name} " + 
                    f"FOREIGN KEY ({field_name}_id) REFERENCES {related_model.__tablename__}(id) ON DELETE CASCADE"
                )
        
        for fk_sql in foreign_keys:
            try:
                cursor.execute(fk_sql)
            except Exception as e:
                cls._logger.error(f"Erro ao adicionar chave estrangeira: {str(e)}")