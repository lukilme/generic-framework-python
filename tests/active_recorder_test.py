from modules.database.active_recorder import BaseModel, ModelMeta, Field
import unittest
from unittest.mock import patch, MagicMock
from modules.database.validator import FormatValidator, LengthValidator, EmailValidator, RangeValidator
from modules.database.active_recorder import BaseModel, ModelMeta, Field, String, Integer, Boolean, ForeignKey, PrimaryKey

class TestValidator(unittest.TestCase):
    """Testes para as classes de validação"""
    
    def test_format_validator(self):
        validator = FormatValidator(r'^[a-z]+$')
        validator.validate('abc')  # Deve passar
        with self.assertRaises(ValueError):
            validator.validate('123')  # Deve falhar
    
    def test_length_validator(self):
        validator = LengthValidator(min_length=2, max_length=5)
        validator.validate('abc')  # Deve passar
        with self.assertRaises(ValueError):
            validator.validate('a')  # Muito curto
        with self.assertRaises(ValueError):
            validator.validate('abcdef')  # Muito longo
    
    def test_email_validator(self):
        validator = EmailValidator()
        validator.validate('test@example.com')  # Deve passar
        with self.assertRaises(ValueError):
            validator.validate('invalid_email')  # Deve falhar
    
    def test_range_validator(self):
        validator = RangeValidator(min_value=1, max_value=10)
        validator.validate(5)  # Deve passar
        with self.assertRaises(ValueError):
            validator.validate(0)  # Menor que o mínimo
        with self.assertRaises(ValueError):
            validator.validate(11)  # Maior que o máximo

class TestField(unittest.TestCase):
    """Testes para a classe Field e suas subclasses"""
    def test_field_initialization(self):
        field = Field('TEXT')
        self.assertEqual(field.field_type, 'TEXT')
        self.assertEqual(field.validators, [])
    
    def test_field_with_validators(self):
        validator = LengthValidator(max_length=10)
        field = Field('TEXT', validators=[validator])
        self.assertEqual(len(field.validators), 1)
        self.assertEqual(field.validators[0], validator)
    
    def test_string_field(self):
        field = String(max_length=100)
        self.assertEqual(field.field_type, 'VARCHAR(100)')
    
    def test_integer_field(self):
        field = Integer()
        self.assertEqual(field.field_type, 'INTEGER')
    
    def test_boolean_field(self):
        field = Boolean()
        self.assertEqual(field.field_type, 'BOOLEAN')
    
    def test_field_validation(self):
        validator = MagicMock()
        field = Field('TEXT', validators=[validator])
        field.validate('test')
        validator.validate.assert_called_once_with('test')

class TestBaseModel(unittest.TestCase):
    """Testes para a classe BaseModel"""
    
    def setUp(self):
        class User(BaseModel):
            name = String(validators=[LengthValidator(min_length=2, max_length=50)])
            age = Integer(validators=[RangeValidator(min_value=0, max_value=120)])
            email = String(validators=[EmailValidator()])
        
        self.user_class = User
    
    def test_model_metaclass(self):
        # Verificar se os campos foram corretamente registrados
        self.assertIn('name', self.user_class._fields)
        self.assertIn('age', self.user_class._fields)
        self.assertIn('email', self.user_class._fields)

        self.assertIsInstance(self.user_class._fields['name'], String)
        self.assertIsInstance(self.user_class._fields['age'], Integer)
        self.assertIsInstance(self.user_class._fields['email'], String)
    
    def test_model_initialization(self):
        user = self.user_class(name='John', age=30, email='john@example.com')
        self.assertEqual(user.name, 'John')
        self.assertEqual(user.age, 30)
        self.assertEqual(user.email, 'john@example.com')
    
    def test_model_validation_success(self):
        user = self.user_class(name='John', age=30, email='john@example.com')
        try:
            user.validate()
        except Exception as e:
            self.fail(f"Validação falhou inesperadamente: {e}")
    
    def test_model_validation_failure(self):
        # Nome muito curto
        user = self.user_class(name='J', age=30, email='john@example.com')
        with self.assertRaises(ValueError):
            user.validate()
        
        # Idade negativa
        user = self.user_class(name='John', age=-5, email='john@example.com')
        with self.assertRaises(ValueError):
            user.validate()
        
        # Email inválido
        user = self.user_class(name='John', age=30, email='invalid_email')
        with self.assertRaises(ValueError):
            user.validate()
    
    @patch.object(BaseModel, 'validate')
    def test_save_calls_validate(self, mock_validate):
        user = self.user_class(name='John', age=30, email='john@example.com')
        user.save()
        mock_validate.assert_called_once()

class TestForeignKeyAndPrimaryKey(unittest.TestCase):
    """Testes para ForeignKey e PrimaryKey"""
    
    def setUp(self):
        class Department(BaseModel):
            name = String()
        
        class Employee(BaseModel):
            name = String()
            department = ForeignKey(Department)
            id = PrimaryKey(Employee)
        Employee.id = PrimaryKey(Employee)

        self.Department = Department
        self.Employee = Employee
    
    def test_foreign_key_initialization(self):
        dept_field = self.Employee._fields['department']
        self.assertIsInstance(dept_field, ForeignKey)
        self.assertEqual(dept_field.model, self.Department)
    
    def test_primary_key_initialization(self):
        id_field = self.Employee._fields['id']
        self.assertIsInstance(id_field, PrimaryKey)
        self.assertEqual(id_field.model, self.Employee)

if __name__ == '__main__':
    unittest.main()