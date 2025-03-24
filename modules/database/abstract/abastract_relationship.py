class AbstractRelationship(ABC):
    def __init__(self, model_class, back_populates=None):
        self.model_class = model_class
        self.back_populates = back_populates
        self.parent_model = None
        self.attribute_name = None
    
    def contribute_to_class(self, model, name):
        self.parent_model = model
        self.attribute_name = name
    
    def get_related_model(self):
        from functools import lru_cache
        
        @lru_cache
        def _get_model():
            for subclass in BaseModel.__subclasses__():
                if subclass.__name__ == self.model_class:
                    return subclass
            raise ValueError(f"Modelo {self.model_class} não encontrado")
        
        return _get_model()