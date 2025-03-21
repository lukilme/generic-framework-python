import unittest
from unittest.mock import patch, Mock, MagicMock
import psycopg2
from psycopg2 import OperationalError
from modules.database.connection import DatabaseConnection, DatabaseError


from contextlib import contextmanager

class TestDatabaseConnection(unittest.TestCase):
    
    def setUp(self):
        DatabaseConnection._instance = None
    
    @patch('psycopg2.connect')
    def test_singleton_pattern(self, mock_connect):
        db1 = DatabaseConnection()
        db2 = DatabaseConnection()
        self.assertIs(db1, db2)
    
    @patch('psycopg2.connect')
    def test_initialize_connection(self, mock_connect):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        db = DatabaseConnection()
        db._initialize_connection()
        
        mock_connect.assert_called_once_with(
            dbname="teste",
            user="admin",
            password="admin",
            host="localhost",
            keepalives=1
        )
        
        self.assertEqual(db._conn, mock_conn)
    
    @patch('psycopg2.connect')
    def test_initialize_connection_error(self, mock_connect):
        mock_connect.side_effect = OperationalError("Erro de conexão simulado")
        
        db = DatabaseConnection()
        with self.assertRaises(ConnectionError):
            db._initialize_connection()
    
    @patch('psycopg2.connect')
    def test_get_connection_new(self, mock_connect):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        db = DatabaseConnection()
        db._conn = None
        
        conn = db.get_connection()
        
        mock_connect.assert_called_once()
        self.assertEqual(conn, mock_conn)
    
    @patch('psycopg2.connect')
    def test_get_connection_closed(self, mock_connect):
        mock_conn = Mock()
        mock_conn.closed = True
        mock_new_conn = Mock()
        
        db = DatabaseConnection()
        db._conn = mock_conn
        
        mock_connect.return_value = mock_new_conn
        
        conn = db.get_connection()
        
        mock_connect.assert_called_once()
        self.assertEqual(conn, mock_new_conn)
    
    @patch('psycopg2.connect')
    def test_get_connection_existing(self, mock_connect):
        mock_conn = Mock()
        mock_conn.closed = False
        
        db = DatabaseConnection()
        db._conn = mock_conn
        
        conn = db.get_connection()
        mock_connect.assert_not_called()
        self.assertEqual(conn, mock_conn)
    
    @patch.object(DatabaseConnection, 'get_connection')
    def test_get_cursor_success(self, mock_get_connection):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        db = DatabaseConnection()
        
        with db.get_cursor() as cursor:
            self.assertEqual(cursor, mock_cursor)
        
        mock_conn.cursor.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch.object(DatabaseConnection, 'get_connection')
    def test_get_cursor_without_commit(self, mock_get_connection):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        db = DatabaseConnection()

        with db.get_cursor(commit=False) as cursor:
            self.assertEqual(cursor, mock_cursor)
        
        mock_conn.commit.assert_not_called()
        mock_cursor.close.assert_called_once()
    

    @patch.object(DatabaseConnection, 'get_connection')
    def test_get_cursor_exception(self, mock_get_connection):
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        db = DatabaseConnection()
        
        with self.assertRaises(DatabaseError):
            with db.get_cursor() as cursor:
                raise ValueError("Erro simulado")
        
        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.commit.assert_not_called()

if __name__ == '__main__':
    unittest.main()