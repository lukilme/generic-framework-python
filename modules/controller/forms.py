import re
from inspect import getmembers

class Field:
    def __init__(self, required=True, label=None, validators=None):
        self.required = required
        self.label = label
        self.validators = validators or []
        self.name = None
        self.value = None
        self.errors = []
    
    def validate(self, value):
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
        if not super().validate(value):
            return False
        
        if value is not None and value != '':
            if self.min_length and len(value) < self.min_length:
                self.errors.append(f"O campo {self.name} deve ter pelo menos {self.min_length} caracteres")
            
            if self.max_length and len(value) > self.max_length:
                self.errors.append(f"O campo {self.name} deve ter no máximo {self.max_length} caracteres")
        
        return len(self.errors) == 0

class EmailField(StringField):
    
    def validate(self, value):
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
    
    def __init__(self, data=None):
        self.data = data or {}
        self.errors = {}
        
        for name, field in self._get_fields():
            field.name = name
    
    def _get_fields(self):
        fields = []
        for name, field in inspect.getmembers(self.__class__):
            if isinstance(field, Field):
                fields.append((name, field))
        return fields
    
    def validate(self):
        is_valid = True
        
        for name, field in self._get_fields():
            value = self.data.get(name)
            if not field.validate(value):
                self.errors[name] = field.errors
                is_valid = False
        
        return is_valid
