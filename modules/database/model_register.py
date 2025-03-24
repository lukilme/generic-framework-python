class ModelRegistry:
    _models = {}
    
    @classmethod
    def register(cls, model):
        cls._models[model.__name__] = model
    
    @classmethod
    def get_model(cls, name):
        return cls._models.get(name)
    
    @classmethod
    def get_all_models(cls):
        return list(cls._models.values())