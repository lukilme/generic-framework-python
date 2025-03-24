import json
from typing import Type, List, Optional, Any, Dict, Tuple

class Response:
    """Representa uma resposta HTTP."""
    def __init__(self, status: str = "200 OK", body: str = "", 
                 headers: List[tuple] = None, content_type: str = "text/html"):
        self.status = status
        self.body = body
        
        if headers is None:
            headers = []

        self.headers = [('Content-Type', content_type)]
        for header in headers:
            self.headers.append(header)
        
    def add_header(self, name: str, value: str):
        """Adiciona um cabeçalho à resposta."""
        self.headers.append((name, value))
        
    @classmethod
    def json(cls, data: Any, status: str = "200 OK"):
        """Cria uma resposta JSON."""
        return cls(
            status=status,
            body=json.dumps(data),
            content_type="application/json"
        )
        
    @classmethod
    def html(cls, content: str, status: str = "200 OK"):
        """Cria uma resposta HTML."""
        return cls(
            status=status,
            body=content,
            content_type="text/html"
        )
        
    @classmethod
    def text(cls, content: str, status: str = "200 OK"):
        """Cria uma resposta de texto simples."""
        return cls(
            status=status,
            body=content,
            content_type="text/plain"
        )
        
    @classmethod
    def redirect(cls, location: str, status: str = "302 Found"):
        """Cria uma resposta de redirecionamento."""
        return cls(
            status=status,
            headers=[('Location', location)],
            body=""
        )

Response.status_messages = {
    200: "OK",
    201: "Created",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error"
}

class ResponseFactory:    
    @staticmethod
    def create_response(status_code: int, body: Any = None, 
                        headers: Dict[str, str] = None) -> Response:
        status = f"{status_code} {Response.status_messages.get(status_code, 'Unknown')}"
        
        if isinstance(body, dict) or isinstance(body, list):
            return Response.json(body, status)
        elif isinstance(body, str):
            return Response.html(body, status)
        else:
            return Response(status=status)
    
    @staticmethod
    def create_error_response(status_code: int, message: str) -> Response:
        return Response.json({"error": message}, 
                             f"{status_code} {Response.status_messages.get(status_code, 'Error')}")

