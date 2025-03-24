import socket
from typing import Optional, Dict, List, Any, Callable, Tuple, Type
from wsgiref.simple_server import make_server
from urllib.parse import parse_qs
import json
import re
import time
import uuid
import inspect
from abc import ABC, abstractmethod
from functools import wraps

import json
from urllib.parse import parse_qs

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

# Definição de códigos de status HTTP
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
    """Fábrica para criar diferentes tipos de respostas."""
    
    @staticmethod
    def create_response(status_code: int, body: Any = None, 
                        headers: Dict[str, str] = None) -> Response:
        """Cria uma resposta baseada no código de status e corpo."""
        status = f"{status_code} {Response.status_messages.get(status_code, 'Unknown')}"
        
        if isinstance(body, dict) or isinstance(body, list):
            return Response.json(body, status)
        elif isinstance(body, str):
            return Response.html(body, status)
        else:
            return Response(status=status)
    
    @staticmethod
    def create_error_response(status_code: int, message: str) -> Response:
        """Cria uma resposta de erro."""
        return Response.json({"error": message}, 
                             f"{status_code} {Response.status_messages.get(status_code, 'Error')}")


# Padrão Singleton para sessões
class SessionManager:

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance.sessions = {}
            cls._instance.session_timeout = 1800  # 30 minutos
        return cls._instance
    
    def create_session(self, user_data: Dict[str, Any] = None) -> str:
        """Cria uma nova sessão."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'data': user_data or {},
            'created_at': time.time(),
            'last_access': time.time()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtém dados de uma sessão."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Verifica se a sessão expirou
            if time.time() - session['last_access'] > self.session_timeout:
                self.destroy_session(session_id)
                return None
            
            # Atualiza o último acesso
            session['last_access'] = time.time()
            return session['data']
        
        return None
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Atualiza dados de uma sessão."""
        if session_id in self.sessions:
            self.sessions[session_id]['data'].update(data)
            self.sessions[session_id]['last_access'] = time.time()
            return True
        return False
    
    def destroy_session(self, session_id: str) -> bool:
        """Destrói uma sessão."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove sessões expiradas."""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session['last_access'] > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            self.destroy_session(session_id)

# Nova implementação: Sistema de Autenticação
class AuthManager:
    """Gerencia autenticação e autorização de usuários."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthManager, cls).__new__(cls)
            cls._instance.users = {}
            cls._instance.roles = {}
        return cls._instance
    
    def register_user(self, username: str, password: str, roles: List[str] = None):
        """Registra um novo usuário."""
        # Em produção, a senha deve ser armazenada com hash e salt
        self.users[username] = {
            'password': password,
            'roles': roles or []
        }
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Autentica um usuário."""
        if username in self.users and self.users[username]['password'] == password:
            user_data = {
                'username': username,
                'roles': self.users[username]['roles']
            }
            return user_data
        return None
    
    def has_role(self, user_data: Dict[str, Any], role: str) -> bool:
        """Verifica se um usuário tem um determinado papel."""
        if user_data and 'roles' in user_data:
            return role in user_data['roles']
        return False


# Nova implementação: Middleware de Sessão
class SessionMiddleware:
    """Middleware para gerenciar sessões."""
    def __init__(self, cookie_name='session_id'):
        self.session_manager = SessionManager()
        self.cookie_name = cookie_name
    
    def process_request(self, request: Request):
        """Processa a requisição, carregando dados da sessão."""
        # Inicializa a sessão como None
        request.session = None
        request.user = None
        
        # Verifica se há um cookie de sessão
        cookies = {}
        cookie_header = request.environ.get('HTTP_COOKIE', '')
        
        for cookie in cookie_header.split(';'):
            if '=' in cookie.strip():  # Add .strip() to handle spaces
                name, value = cookie.strip().split('=', 1)
                cookies[name] = value
        
        session_id = cookies.get(self.cookie_name)
        
        if session_id:
            session_data = self.session_manager.get_session(session_id)
            request.session = session_data
            # Set the request.user from the session data
            if session_data and 'user' in session_data:
                request.user = session_data.get('user')
        
        return request
    
    def process_response(self, request: Request, response: Response) -> Response:
        """Processa a resposta, atualizando cookies de sessão se necessário."""
        if request.session:
            cookies = {}
            cookie_header = request.environ.get('HTTP_COOKIE', '')
            
            for cookie in cookie_header.split(';'):
                if '=' in cookie.strip():
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
            
            if self.cookie_name not in cookies:
                for session_id, session_data in self.session_manager.sessions.items():
                    if session_data.get('data') == request.session:
                        response.add_header('Set-Cookie', f"{self.cookie_name}={session_id}; Path=/; HttpOnly")
                        break
        
        return response


def require_auth(role: str = None):
    def decorator(handler):
        @wraps(handler)
        def wrapper(self, request, *args, **kwargs):
            print(request)
            if not request.user:
                print("Nope")
                return Response.redirect('/login')
            
            if role and not AuthManager().has_role(request.user, role):
                return ResponseFactory.create_error_response(403, "Permissão negada")
            
            return handler(self, request, *args, **kwargs)
        return wrapper
    return decorator

class Field:
    """Base para campos de formulário."""
    def __init__(self, required=True, label=None, validators=None):
        self.required = required
        self.label = label
        self.validators = validators or []
        self.name = None
        self.value = None
        self.errors = []
    
    def validate(self, value):
        """Valida o valor do campo."""
        self.value = value
        self.errors = []
        
        if self.required and (value is None or value == ''):
            self.errors.append(f"O campo {self.name} é obrigatório")
            return False
        
        for validator in self.validators:
            result = validator(value)
            if isinstance(result, str): 
                self.errors.append(result)
        
        return len(self.errors) == 0


class StringField(Field):
    def __init__(self, min_length=None, max_length=None, **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value):
        """Valida o valor do campo."""
        if not super().validate(value):
            return False
        
        if value is not None and value != '':
            if self.min_length and len(value) < self.min_length:
                self.errors.append(f"O campo {self.name} deve ter pelo menos {self.min_length} caracteres")
            
            if self.max_length and len(value) > self.max_length:
                self.errors.append(f"O campo {self.name} deve ter no máximo {self.max_length} caracteres")
        
        return len(self.errors) == 0

class EmailField(StringField):
    """Campo de email."""
    
    def validate(self, value):
        """Valida se o valor é um email válido."""
        if not super().validate(value):
            return False
        
        if value and not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', value):
            self.errors.append(f"O campo {self.name} deve ser um email válido")
        
        return len(self.errors) == 0

class IntegerField(Field):
    def __init__(self, min_value=None, max_value=None, **kwargs):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value):
        if not super().validate(value):
            return False
        
        try:
            if value is not None and value != '':
                int_value = int(value)
                
                if self.min_value is not None and int_value < self.min_value:
                    self.errors.append(f"O campo {self.name} deve ser maior ou igual a {self.min_value}")
                
                if self.max_value is not None and int_value > self.max_value:
                    self.errors.append(f"O campo {self.name} deve ser menor ou igual a {self.max_value}")
        except ValueError:
            self.errors.append(f"O campo {self.name} deve ser um número inteiro")
        
        return len(self.errors) == 0

class Form:
    """Base para definição de formulários."""
    
    def __init__(self, data=None):
        self.data = data or {}
        self.errors = {}
        
        for name, field in self._get_fields():
            field.name = name
    
    def _get_fields(self):
        """Obtém todos os campos do formulário."""
        fields = []
        for name, field in inspect.getmembers(self.__class__):
            if isinstance(field, Field):
                fields.append((name, field))
        return fields
    
    def validate(self):
        """Valida todos os campos do formulário."""
        is_valid = True
        
        for name, field in self._get_fields():
            value = self.data.get(name)
            if not field.validate(value):
                self.errors[name] = field.errors
                is_valid = False
        
        return is_valid

class Controller:
    """Classe base para controladores."""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.session_manager = SessionManager()
    
    def get_current_user(self, request: Request):
        """Obtém o usuário atual da requisição."""
        if request.session and 'user' in request.session:
            return request.session['user']
        return None
    
    def login_user(self, request: Request, username: str, password: str) -> bool:
        """Autentica um usuário e inicia uma sessão."""
        user_data = self.auth_manager.authenticate(username, password)
        if user_data:
            session_id = self.session_manager.create_session({'user': user_data})
            if(user_data['username']=='admin'):
                response = Response.redirect('/admin')
            else:
                response = Response.redirect('/dashboard')
            response.add_header('Set-Cookie', f'session_id={session_id}; Path=/; HttpOnly')
            return response 
        return False

    def logout_user(self, request: Request) -> Response:
        """Encerra a sessão do usuário e redireciona para a página de login."""
        cookies = {}
        cookie_header = request.environ.get('HTTP_COOKIE', '')
        
        for cookie in cookie_header.split(';'):
            if '=' in cookie.strip():
                name, value = cookie.strip().split('=', 1)
                cookies[name] = value
        
        session_id = cookies.get('session_id')
        
        if session_id:
            success = self.session_manager.destroy_session(session_id)
            if success:
                # Create a response that also clears the cookie
                response = Response.redirect('/login')
                response.add_header('Set-Cookie', 'session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly')
                return response

class Router:
    """Gerencia o roteamento de requisições para controladores."""
    
    def __init__(self):
        self.routes = []
        self.middlewares = []
    
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
    
    def add_middleware(self, middleware):
        """Adiciona um middleware ao roteador."""
        self.middlewares.append(middleware)
    
    def dispatch(self, request: Request) -> Response:
        """Despacha a requisição para o handler apropriado."""
        # Aplica middlewares na requisição
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
        
        # Rota não encontrada
        return ResponseFactory.create_error_response(404, "Not Found")


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
        """Registra rotas no roteador."""
        self.router.register_routes(routes)
    
    def add_middleware(self, middleware):
        """Adiciona um middleware ao servidor."""
        self.router.add_middleware(middleware)


# Exemplo de uso
def example_usage():
    # Cria o servidor
    server = Server(host="localhost", port=8000)
    
    # Inicializa o gerenciador de autenticação
    auth_manager = AuthManager()
    auth_manager.register_user("admin", "senha123", ["admin"])
    auth_manager.register_user("user", "user123", ["user"])
    
    # Exemplo de formulário de login
    class LoginForm(Form):
        username = StringField(required=True)
        password = StringField(required=True)
    
    # Exemplo de controlador
    class UserController(Controller):

        def login(self, request: Request) -> Response:
            if request.method == "GET":
                return Response.html("""
                <form method="post" action="/login">
                    <input type="text" name="username" value="user" placeholder="Nome de usuário"><br>
                    <input type="password" name="password" value="user123" placeholder="Senha"><br>
                    <button type="submit">Entrar</button>
                </form>
                """)
            elif request.method == "POST":
                form_data = {}
                if request.body:
                    if isinstance(request.body, dict):
                        for key, value in request.body.items():
                            if isinstance(value, list) and value:
                                form_data[key] = value[0]
                            else:
                                form_data[key] = value
                
                form = LoginForm(form_data)
                if form.validate():
                    username = form.username.value
                    password = form.password.value
                    response = self.login_user(request, username, password)
                    if response:  # If login_user returns a Response, return it directly
                        return response
                    else:
                        return Response.html("<p>Usuário ou senha inválidos.</p>")
                else:
                    return Response.html(f"<p>Erros no formulário: {form.errors}</p>")
                
        @require_auth()
        def dashboard(self, request: Request) -> Response:
            user = request.user  # Corrigido: usar request.user em vez de self.user
            return Response.html(f"<h1>Bem-vindo ao painel, {user['username']}!</h1>")
        
        @require_auth(role="admin")
        def admin_area(self, request: Request) -> Response:
            return Response.html("<h1>Área do Administrador</h1>")
    
    user_controller = UserController()
    

    routes = {
        "/": {
            "GET": lambda request: Response.html("<h1>Bem-vindo ao meu framework web!</h1>"),
        },
        "/login": {
            "GET": user_controller.login,
            "POST": user_controller.login,
        },
        "/dashboard": {
            "GET": user_controller.dashboard,
        },
        "/admin": {
            "GET": user_controller.admin_area,
        },
        "/logout":{
            "GET": user_controller.logout_user,
        },
        "/hello": {
            "GET": lambda request: Response.text("Olá, mundo!"),
        },
        "/greet/{name}": {
            "GET": lambda request: Response.text(f"Olá, {request.url_params['name']}!"),
        },
        "/json": {
            "GET": lambda request: Response.json({"message": "Isso é um JSON!"}),
        },
    }
    
    server.register_routes(routes)
    server.start()

if __name__ == "__main__":
    example_usage()