




def adicionar_info(nivel_acesso): 
    def decorator(classe): 
        def exibir_info(self):
            print(f"Informações da classe ({nivel_acesso}): {classe.__name__}")
            for atributo, valor in self.__dict__.items():
                print(f"{atributo}: {valor}")
        classe.exibir_info = exibir_info
        return classe
    return decorator

@adicionar_info("secreto") 
class Pessoa:
    def __init__(self, nome, idade, senha):
        self.nome = nome
        self.idade = idade
        self._senha = senha 

pessoa = Pessoa("Alice", 30, "123456")
pessoa.exibir_info()