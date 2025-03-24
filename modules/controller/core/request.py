from urllib.parse import parse_qs
import json

class Request:
    """Representa uma requisição HTTP."""
    
    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get('REQUEST_METHOD', 'GET')
        self.path = environ.get('PATH_INFO', '/')
        self.query_params = parse_qs(environ.get('QUERY_STRING', ''))
        self.url_params = {}
        self.session = None
        self.user = None
        
        # Carrega o corpo da requisição se necessário
        self.body = None
        if self.method in ['POST', 'PUT']:
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                content_type = environ.get('CONTENT_TYPE', '')
                
                if content_length > 0:
                    body = environ['wsgi.input'].read(content_length)
                    
                    if 'application/json' in content_type:
                        self.body = json.loads(body)
                    elif 'application/x-www-form-urlencoded' in content_type:
                        self.body = parse_qs(body.decode('utf-8'))
                    else:
                        self.body = body.decode('utf-8')
            except Exception:
                self.body = None