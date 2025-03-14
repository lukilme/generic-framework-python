class Validator:
    def validate(self, value):
        raise NotImplementedError

class RequiredValidator(Validator):
    def validate(self, value):
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValueError("Campo obrigatório")
        return True

class TypeValidator(Validator):
    def __init__(self, expected_type):
        self.expected_type = expected_type
        
    def validate(self, value):
        if value is not None and not isinstance(value, self.expected_type):
            raise TypeError(f"Valor deve ser do tipo {self.expected_type.__name__}")
        return True

class LengthValidator(Validator):
    def __init__(self, min_length=None, max_length=None):
        self.min_length = min_length
        self.max_length = max_length
        
    def validate(self, value):
        if value is None:
            return True

        if not hasattr(value, "__len__"):
            raise TypeError("Valor não suporta validação de comprimento")
            
        if self.min_length is not None and len(value) < self.min_length:
            raise ValueError(f"Comprimento mínimo é {self.min_length}")
            
        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"Comprimento máximo é {self.max_length}")
            
        return True

class FormatValidator(Validator):
    def __init__(self, pattern):
        import re
        self.pattern = re.compile(pattern)
        
    def validate(self, value):
        if value is None:
            return True
            
        if not isinstance(value, str):
            raise TypeError("Valor deve ser uma string")
            
        if not self.pattern.match(value):
            raise ValueError("Formato inválido")
            
        return True

class EmailValidator(FormatValidator):
    def __init__(self):
        super().__init__(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
        
    def validate(self, value):
        try:
            super().validate(value)
        except ValueError:
            raise ValueError("Email inválido")
        return True

class RangeValidator(Validator):
    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value
        
    def validate(self, value):
        if value is None:
            return True
            
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Valor mínimo é {self.min_value}")
            
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Valor máximo é {self.max_value}")
            
        return True

class InclusionValidator(Validator):
    def __init__(self, valid_values):
        self.valid_values = valid_values
        
    def validate(self, value):
        if value is not None and value not in self.valid_values:
            raise ValueError(f"Valor deve estar entre: {', '.join(str(v) for v in self.valid_values)}")
        return True
