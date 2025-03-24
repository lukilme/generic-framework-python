from urllib.parse import parse_qs
import json

class Request:
    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get('REQUEST_METHOD', 'GET')
        self.path = environ.get('PATH_INFO', '/')
        self.query_params = parse_qs(environ.get('QUERY_STRING', ''))
        self.url_params = {}
        self.session = None
        self.user = None
        
        self.body = None
        if self.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
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

    def get_form_value(self, field_name: str, default=None):
        if self.body is None:
            return default
        
        if isinstance(self.body, dict):
            if field_name in self.body:
                return self.body.get(field_name, default)
        
        elif isinstance(self.body, dict) and field_name in self.body:
            values = self.body.get(field_name)
            if isinstance(values, list) and values:
                return values[0]
            return values
        
        return default

    def __str__(self):
        return (
            f"Request(method={self.method}, path={self.path}, "
            f"query_params={json.dumps(self.query_params)}, "
            f"url_params={self.url_params}, body={json.dumps(self.body)})"
        )
