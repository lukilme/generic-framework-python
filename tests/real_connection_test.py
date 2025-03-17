import unittest
import os
import psycopg2
from contextlib import contextmanager
import uuid
from psycopg2 import OperationalError
from modules.database.connection import DatabaseConnection, DatabaseError


class TestDatabaseIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseConnection()
        
        cls.table_name = f"test_table_{uuid.uuid4().hex[:8]}"
        
        with cls.db.get_cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE {cls.table_name} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    age INTEGER,
                    active BOOLEAN DEFAULT true
                )
            """)
    
    @classmethod
    def tearDownClass(cls):
        with cls.db.get_cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {cls.table_name}")
        
        conn = cls.db.get_connection()
        if conn and not conn.closed:
            conn.close()
    
    def test_1_insert_data(self):
        with self.db.get_cursor() as cursor:
            placehoulder = f"INSERT INTO {self.table_name} (name, age, active) VALUES (%s, %s, %s) RETURNING id"
            cursor.execute(placehoulder,("Alice", 30, True))
            id_alice = cursor.fetchone()[0]
            
            cursor.execute(placehoulder,("Bob", 25, True))
            id_bob = cursor.fetchone()[0]
            
            cursor.execute(placehoulder,("Charlie", 35, False))
            id_charlie = cursor.fetchone()[0]
        
        self.assertIsNotNone(id_alice)
        self.assertIsNotNone(id_bob)
        self.assertIsNotNone(id_charlie)
        print(id_alice,id_bob,id_charlie)
        
        self.id_alice = id_alice
        self.id_bob = id_bob
        self.id_charlie = id_charlie
    
    def test_2_select_data(self):
        with self.db.get_cursor(commit=False) as cursor:
            cursor.execute(f"SELECT * FROM {self.table_name} ORDER BY id")
            rows = cursor.fetchall()
            
            self.assertEqual(len(rows), 3)
            
            self.assertEqual(rows[0][1], "Alice")
            self.assertEqual(rows[0][2], 30)
            self.assertTrue(rows[0][3])
            
            self.assertEqual(rows[1][1], "Bob")
            self.assertEqual(rows[1][2], 25)
            self.assertTrue(rows[1][3])
            
            self.assertEqual(rows[2][1], "Charlie")
            self.assertEqual(rows[2][2], 35)
            self.assertFalse(rows[2][3])
    
    def test_3_update_data(self):
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"UPDATE {self.table_name} SET age = %s, active = %s WHERE name = %s",
                (31, False, "Alice")
            )
            rows_affected = cursor.rowcount
            self.assertEqual(rows_affected, 1)
            
            cursor.execute(f"SELECT age, active FROM {self.table_name} WHERE name = %s", ("Alice",))
            row = cursor.fetchone()
            self.assertEqual(row[0], 31)
            self.assertFalse(row[1])
    
    def test_4_delete_data(self):
        """Testa a remoção de dados da tabela."""
        with self.db.get_cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.table_name} WHERE name = %s", ("Bob",))
            rows_affected = cursor.rowcount
            self.assertEqual(rows_affected, 1)
            
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
    
    def test_5_transaction_rollback(self):
        """Testa o comportamento de rollback em transações."""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO {self.table_name} (name, age, active) VALUES (%s, %s, %s)",
                    ("David", 40, True)
                )

                cursor.execute("SELECT * FROM non_existent_table")

                self.fail("O teste deveria ter levantado uma exceção")
        except DatabaseError:
            pass
        with self.db.get_cursor(commit=False) as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE name = %s", ("David",))
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
    
    def test_6_create_table(self):
        new_table = f"test_table_new_{uuid.uuid4().hex[:8]}"
        
        with self.db.get_cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE {new_table} (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(10) UNIQUE,
                    description TEXT
                )
            """)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_tables 
                    WHERE tablename = %s
                )
            """, (new_table,))
            exists = cursor.fetchone()[0]
            print(exists)
            self.assertTrue(exists)
            
            cursor.execute(f"DROP TABLE {new_table}")

if __name__ == '__main__':
    unittest.main()