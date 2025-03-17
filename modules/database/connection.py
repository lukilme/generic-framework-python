from contextlib import contextmanager
import psycopg2
from psycopg2 import OperationalError

class DatabaseError(Exception):
    pass

class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._conn = None
        return cls._instance

    def _initialize_connection(self):
        ''' Conexão '''
        try:
            self._conn = psycopg2.connect(
                dbname="teste",
                user="admin",
                password="admin",
                host="localhost",
                keepalives=1  
            )
        except OperationalError as e:
            raise ConnectionError(f"Database connection failed: {e}")

    def get_connection(self):
        if not self._conn or self._conn.closed:
            self._initialize_connection()
        return self._conn

    @contextmanager
    def get_cursor(self, commit: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Transaction failed: {e}") from e
        finally:
            cursor.close()