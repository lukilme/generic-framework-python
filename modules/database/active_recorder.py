from modules.database.validator import Validator,FormatValidator,LengthValidator, EmailValidator, RangeValidator
from typing import Dict, List, Type, Optional

class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name != 'BaseModel':
            fields = {}
            for key, value in attrs.items():
                if isinstance(value, Field):
                    fields[key] = value
            attrs['_fields'] = fields
        return super().__new__(cls, name, bases, attrs)
    
    def __init__(cls, name, bases, attrs):
        print("")

class BaseModel(metaclass=ModelMeta):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def save(self):
        self.validate()

    def validate(self):
        for field_name, field in self._fields.items():
            value = getattr(self, field_name, None)
            field.validate(value)

class Field:
    def __init__(self, field_type, validators: list[Validator] = None):
        self.field_type = field_type
        self.validators = validators or []

    def validate(self, value):
        for validator in self.validators:
            validator.validate(value)

class String(Field):
    def __init__(self, max_length=255, **kwargs):
        super().__init__('VARCHAR({})'.format(max_length), **kwargs)

class Integer(Field):
    def __init__(self, **kwargs):
        super().__init__('INTEGER', **kwargs)

class Boolean(Field):
    def __init__(self, **kwargs):
        super().__init__('BOOLEAN', **kwargs)

class ForeignKey(Field):
    def __init__(self, model: Type[BaseModel], **kwargs):
        super().__init__('VARCHAR({})', **kwargs)
        self.model = model

class PrimaryKey(Field):
    def __init__(self, model: Type[BaseModel], **kwargs):
        super().__init__('VARCHAR({})', **kwargs)
        self.model = model