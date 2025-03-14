class DatabaseConnection:
    def __new__(cls, *args, **kwargs):
        print(f"Criando uma instância de {cls.__name__}")
        return super().__new__(cls)

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        raise NotImplementedError("O método connect() deve ser implementado pela subclasse.")

    def disconnect(self):
        if self.connection:
            print("Fechando conexão com o banco de dados.")
            self.connection = None
        else:
            print("Nenhuma conexão aberta para ser fechada.")