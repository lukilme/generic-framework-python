import psycopg2
from psycopg2.extras import RealDictCursor
from modules.utils.logger import Logger

class DatabaseConnection:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, host="localhost", database="teste", user="admin", password="admin"):
        if getattr(self, '_initialized', False):
            return
        
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self._connection = None
        self._logger = Logger("DatabaseConnection")
        self._initialized = True
    
    def connect(self):
        self._logger.info(f"Conectando ao banco de dados {self.database} em {self.host}")
        self._connection = psycopg2.connect(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password
        )
        return self._connection
    
    def get_connection(self):
        if self._connection is None or self._connection.closed:
            self.connect()
        return self._connection
    
    def execute_query(self, query, params=None):
        self._logger.debug(f"Executando query: {query} com parâmetros: {params}")
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith(("SELECT", "RETURNING")):
                results = [dict(row) for row in cursor.fetchall()]
                self._logger.debug(f"Resultados da query: {results}")
                return results
            conn.commit()
            self._logger.debug(f"Query executada com sucesso, {cursor.rowcount} linhas afetadas")
            return cursor.rowcount