from wsgiref.simple_server import make_server
from .routing import Router
from .request import Request
from .seassions import SessionMiddleware

class Server:
    def __init__(self, host: str = 'localhost', port: int = 8000):
        self.host = host
        self.port = port
        self.router = Router()
        self.running = False
        self.router.add_middleware(SessionMiddleware())
    
    def start(self):
        self.running = True
        server = make_server(self.host, self.port, self.application)
        print(f"Servidor iniciado em http://{self.host}:{self.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Servidor encerrado")
        
    def application(self, environ, start_response):
        request = Request(environ)
        response = self.router.dispatch(request)
        print(response)
        start_response(response.status, response.headers)
        return [response.body.encode('utf-8')]
        
    def register_routes(self, routes):
        self.router.register_routes(routes)
    
    def add_middleware(self, middleware):
        self.router.add_middleware(middleware)
