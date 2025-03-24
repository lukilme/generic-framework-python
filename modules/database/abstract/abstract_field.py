from abc import ABC, abstractmethod

class AbstractField(ABC):
    def __init__(self, required=False, unique=False):
        self.required = required
        self.unique = unique
    
    @abstractmethod
    def validate(self, value):
        if self.required and value is None:
            raise ValueError(f"Campo obrigatório não pode ser nulo")
    
    @abstractmethod
    def get_sql_definition(self):
        pass

class AbstractValueField(AbstractField):    
    @abstractmethod
    def to_python(self, value):
        pass
    
    @abstractmethod
    def to_db(self, value):
        pass

class AbstractRelationshipField(AbstractField):    
    def __init__(self, model_class, back_populates=None, **kwargs):
        super().__init__(**kwargs)
        self.model_class = model_class
        self.back_populates = back_populates
        self.parent_model = None
        self.attribute_name = None
    
    def contribute_to_class(self, model, name):
        self.parent_model = model
        self.attribute_name = name
    
    @abstractmethod
    def get_related_model(self):
        pass