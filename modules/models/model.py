from modules.database import BaseModel, StringField, DateField, ForeignKey
from modules.database import OneToOneField

class Usuario(BaseModel):
    nome = StringField(required=True)
    email = StringField(required=True, unique=True)
    senha = StringField(required=True)
    perfil = OneToOneField("Perfil", back_populates="usuario")

class Perfil(BaseModel):
    bio = StringField()
    data_nascimento = DateField()
    usuario = ForeignKey("Usuario", unique=True, back_populates="perfil")