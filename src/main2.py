from modules.controller.server import Server 
from modules.controller.routing import Router
from modules.controller.response import Response
from modules.controller.request import Request
from modules.controller.controller import BaseController
from modules.controller.auth import require_auth
from modules.controller.auth import AuthManager
from modules.controller.forms import *

def example_usage():
    server = Server(host="localhost", port=8000)
    
    auth_manager = AuthManager()
    auth_manager.register_user("admin", "senha123", ["admin"])
    auth_manager.register_user("user", "user123", ["user"])
    
    class LoginForm(Form):
        username = StringField(required=True)
        password = StringField(required=True)
    
    class UserController(BaseController):

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
                    if response:  
                        return response
                    else:
                        return Response.html("<p>Usuário ou senha inválidos.</p>")
                else:
                    return Response.html(f"<p>Erros no formulário: {form.errors}</p>")
                
        @require_auth()
        def dashboard(self, request: Request) -> Response:
            user = request.user 
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