from modules.utils.logger import Logger
from modules.database.connection import DatabaseConnection
from modules.database.abstract.model_register import ModelRegistry

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
        try:
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
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            conn.rollback()
    
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