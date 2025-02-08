import time

class Pessoa:
    def __init__(self, nome):
        self._velocidade = 1 
        self.nome = nome

    def falar(self):
        print(f"{self.nome} está falando.")

p = Pessoa("Alice")

def adicionar_propriedade():
    def get_velocidade(self):
        return self._velocidade

    def set_velocidade(self, valor):
        print(f"Alterando velocidade para {valor}")
        self._velocidade = valor

    setattr(Pessoa, "velocidade", property(get_velocidade, set_velocidade))

def modificar_propriedade():
    def get_velocidade(self):
        return self._velocidade * 2  

    setattr(Pessoa, "velocidade", property(get_velocidade, Pessoa.velocidade.fset))

for _ in range(3):
    time.sleep(2)
    adicionar_propriedade()  
    print(f"Velocidade inicial: {p.velocidade}")
    
    time.sleep(2)
    modificar_propriedade() 
    print(f"Velocidade modificada: {p.velocidade}")

    p.velocidade = 5  
    print(f"Nova velocidade após set: {p.velocidade}")
