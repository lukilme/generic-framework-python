import re
from typing import Dict, Callable, List, Tuple
from .request import Request
from .response import Response

class Router:
    """Gerencia o roteamento de requisições para controladores."""
    
    def __init__(self):
        self.routes = []
        
    def register_routes(self, routes: Dict[str, Dict[str, Callable]]):
        """Registra rotas no formato {path: {method: handler}}."""
        for path, methods in routes.items():
            for method, handler in methods.items():
                self.add_route(path, method.upper(), handler)
                
    def add_route(self, path: str, method: str, handler: Callable):
        """Adiciona uma rota ao roteador."""
        # Converte caminhos como "/users/{id}" para expressões regulares
        pattern = re.sub(r'{([^/]+)}', r'(?P<\1>[^/]+)', path)
        regex = re.compile(f'^{pattern}$')
        self.routes.append((regex, method, handler))
        
    def dispatch(self, request: Request) -> Response:
        """Despacha a requisição para o handler apropriado."""
        from .response import ResponseFactory
        
        for regex, method, handler in self.routes:
            match = regex.match(request.path)
            if match and request.method == method:
                # Extrai parâmetros da URL
                url_params = match.groupdict()
                request.url_params = url_params
                
                try:
                    return handler(request)
                except Exception as e:
                    return ResponseFactory.create_error_response(500, str(e))
        
        # Rota não encontrada
        return ResponseFactory.create_error_response(404, "Not Found")