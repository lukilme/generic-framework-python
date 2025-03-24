import re
from .request import Request
from .response import Response, ResponseFactory
from typing import Optional, Dict, List, Any, Callable, Tuple, Type


class Router:    
    def __init__(self):
        self.routes = []
        self.middlewares = []
    
    def register_routes(self, routes: Dict[str, Dict[str, Callable]]):
        for path, methods in routes.items():
            for method, handler in methods.items():
                self.add_route(path, method.upper(), handler)
    
    def add_route(self, path: str, method: str, handler: Callable):
        pattern = re.sub(r'{([^/]+)}', r'(?P<\1>[^/]+)', path)
        regex = re.compile(f'^{pattern}$')
        self.routes.append((regex, method, handler))
    
    def add_middleware(self, middleware):
        self.middlewares.append(middleware)
    
    def dispatch(self, request: Request) -> Response:
        for middleware in self.middlewares:
            if hasattr(middleware, 'process_request'):
                request = middleware.process_request(request)
        
        for regex, method, handler in self.routes:
            match = regex.match(request.path)
            if match and request.method == method:
                url_params = match.groupdict()
                request.url_params = url_params
                
                try:
                    response = handler(request)
                except Exception as e:
                    response = ResponseFactory.create_error_response(500, str(e))
                
                for middleware in reversed(self.middlewares):
                    if hasattr(middleware, 'process_response'):
                        response = middleware.process_response(request, response)
                
                return response
            else:
                #tratar caso não
                pass

        return ResponseFactory.create_error_response(404, "Not Found")
