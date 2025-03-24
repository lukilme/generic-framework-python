
from modules.database import DB
from datetime import date

from modules.database.abstract.model_register import ModelRegistry
from modules.database.base_model import BaseModel
from modules.database.fields import *
from modules.database.relationships import OneToOneField, ForeignKey

@ModelRegistry.register
class Usuario(BaseModel):
    nome = StringField(required=True)
    email = StringField(required=True, unique=True)
    senha = StringField(required=True)
    perfil = OneToOneField("Perfil", back_populates="usuario")

@ModelRegistry.register
class Perfil(BaseModel):
    bio = StringField()
    data_nascimento = DateField()
    usuario = ForeignKey("Usuario", unique=True, back_populates="perfil")

DB.connect()

DB.create_tables(ModelRegistry.get_all_models())
UserClass = ModelRegistry.get_model("Usuario")
admin = UserClass(nome="Admin", email="admin@loja.com", senha="admin123")
admin.save()