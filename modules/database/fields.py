from abc import ABC, abstractmethod
from datetime import date

class AbstractField(ABC):
    def __init__(self, required=False, unique=False):
        self.required = required
        self.unique = unique
    
    def validate(self, value):
        if self.required and value is None:
            raise ValueError(f"Campo obrigatório não pode ser nulo")
    
    @abstractmethod
    def get_sql_definition(self):
        """Retorna a definição SQL do campo"""
        pass

class Field(AbstractField):
    def __init__(self, required=False, unique=False):
        super().__init__(required=required, unique=unique)
    
    def validate(self, value):
        super().validate(value)
    
    def get_sql_definition(self):
        return "VARCHAR(255)"  # Implementação padrão

class StringField(Field):
    def __init__(self, max_length=255, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length

    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"Valor deve ser uma string")
        if value is not None and len(value) > self.max_length:
            raise ValueError(
                f"String não pode ter mais que {self.max_length} caracteres"
            )
    
    def get_sql_definition(self):
        return f"VARCHAR({self.max_length})"

class IntegerField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, int):
            raise ValueError(f"Valor deve ser um inteiro")
    
    def get_sql_definition(self):
        return "INTEGER"

class FloatField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError(f"Valor deve ser um número")
    
    def get_sql_definition(self):
        return "REAL"

class BooleanField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"Valor deve ser booleano")
    
    def get_sql_definition(self):
        return "BOOLEAN"

class DateField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, date):
            raise ValueError(f"Valor deve ser uma data")
    
    def get_sql_definition(self):
        return "DATE"