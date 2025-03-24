import socket
from typing import Optional
from .router import Router
from wsgiref.simple_server import make_server
from .request import Request

class Server:
    def __init__(self, host: str = 'localhost', port: int = 8000):
        self.host = host
        self.port = port
        self.router = Router()
        self.running = False
        
    def start(self):
        self.running = True
        server = make_server(self.host, self.port, self.application)
        print(f"Servidor iniciado em http://{self.host}:{self.port}")
        server.serve_forever()
        
    def application(self, environ, start_response):
        request = Request(environ)
        response = self.router.dispatch(request)
        start_response(response.status, response.headers)
        return [response.body.encode('utf-8')]
        
    def register_routes(self, routes):
        self.router.register_routes(routes)