
from modules.database import DB
from datetime import date

from modules.database.abstract.model_register import ModelRegistry
from modules.database.base_model import BaseModel
from modules.database.fields import *
from modules.database.relationships import OneToOneField, ForeignKey, ManyToManyField


class Usuario(BaseModel):
    nome = StringField(required=True)
    email = StringField(required=True, unique=True)
    senha = StringField(required=True)
    perfil = OneToOneField("Perfil", back_populates="usuario")

class Perfil(BaseModel):
    bio = StringField()
    data_nascimento = DateField()
    usuario = ForeignKey("Usuario", unique=True, back_populates="perfil")

class Categoria(BaseModel):
    nome = StringField(required=True)
    descricao = StringField()
    produtos = ManyToManyField("Produto", back_populates="categoria")

class Produto(BaseModel):
    nome = StringField(required=True)
    preco = FloatField(required=True)
    descricao = StringField()
    categoria = ForeignKey("Categoria", back_populates="produtos")
    tag = ManyToManyField("Tag", back_populates="produtos")

class Tag(BaseModel):
    nome = StringField(required=True, unique=True)
    produtos = ManyToManyField(
        "Produto", back_populates="tag"
    ) 

if __name__ == "__main__":
    # DB.create_tables([Usuario, Perfil, Categoria, Produto, Tag])
    DB.create_tables([Usuario, Perfil, Categoria, Tag, Produto])  # Tag antes de Produto
    # Usuario._fields['perfil'] = OneToOneField('Perfil', back_populates='usuario')
    # Categoria._fields['produto'] = ManyToManyField('Produto', back_populates='categoria')
    # Produto._fields['tag'] = ManyToManyField('Tag', back_populates='produto')
    # Criando usuários e perfis (1:1)
    admin = Usuario(nome="Admin", email="admin@loja.com", senha="admin123")
    admin.save()

    admin_perfil = Perfil(
        bio="Administrador da loja virtual",
        data_nascimento=date(1985, 3, 10),
        usuario=admin,
    )
    admin_perfil.save()

    admin._perfil_cache = admin_perfil
    print(f"Perfil do administrador: {admin.perfil.bio}")
    print(f"Email do usuário do perfil: {admin_perfil.usuario.email}")

    informatica = Categoria(nome="Informática", descricao="Produtos de informática")
    informatica.save()

    games = Categoria(nome="Games", descricao="Jogos e consoles")
    games.save()

    notebook = Produto(
        nome="Notebook Ultimate",
        preco=5499.90,
        descricao="Notebook para jogos de alto desempenho",
        categoria=informatica,
    )
    notebook.save()

    console = Produto(
        nome="Console Game Station",
        preco=3999.90,
        descricao="Console de última geração",
        categoria=games,
    )
    console.save()

    tag_gamer = Tag(nome="Gamer")
    tag_gamer.save()

    tag_premium = Tag(nome="Premium")
    tag_premium.save()

    tag_oferta = Tag(nome="Oferta da Semana")
    tag_oferta.save()

    notebook.tag.add(tag_gamer)
    notebook.tag.add(tag_premium)
    console.tag.add(tag_gamer)
    console.tag.add(tag_oferta)

    print(f"Perfil do administrador: {admin.perfil.bio}")
    print(f"Email do usuário do perfil: {admin_perfil.usuario.email}")
    informatica.produtos.add(notebook)
    produtos_informatica = informatica.produtos.get_related_instances()
    print(f"Produtos da categoria Informática:")
    for produto in produtos_informatica:
        print(f"- {produto.nome}: R${produto.preco}")
        print(
            f"  Tags: {', '.join([tag.nome for tag in produto.tag.get_related_instances()])}"
        )

    produtos_gamer = tag_gamer.produtos.get_related_instances()
    print(f"Produtos com a tag Gamer:")
    for produto in produtos_gamer:
        print(f"- {produto.nome} (Categoria: {produto.categoria.nome})")