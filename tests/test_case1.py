import unittest
import datetime
from unittest.mock import patch, MagicMock
import psycopg2
from modules.database.connection import DatabaseConnection
from modules.database.active_recorder import *


class User(BaseModel):
    name = StringField(required=True)
    email = StringField(required=True)

class TestActiveRecord(unittest.TestCase):

    def test_valid_user(self):
        user = User(name="John Doe", email="john@example.com")
        try:
            user.save() 
        except Exception as e:
            self.fail("Salvamento de usuário válido gerou exceção: " + str(e))

    def test_missing_name(self):
        with self.assertRaises(ValueError) as context:
            user = User(email="john@example.com")
            user.save()
        self.assertIn("Field is required", str(context.exception))

    def test_wrong_type_email(self):
        with self.assertRaises(ValueError) as context:
            user = User(name="John Doe", email=123)  
            user.save()
        self.assertIn("Value must be a string", str(context.exception))

if __name__ == '__main__':
    unittest.main()