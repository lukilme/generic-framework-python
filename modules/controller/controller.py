from .auth import AuthManager, require_auth
from .response import Response
from .seassions import SessionManager
from .request import Request
from typing import Optional, Dict, List, Any, Callable, Tuple, Type
from pathlib import Path
from .forms import Form

class BaseController:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.session_manager = SessionManager()
    
    def get_current_user(self, request: Request):
        if request.session and 'user' in request.session:
            return request.session['user']
        return None
    
    def login_user(self, request: Request, username: str, password: str) -> bool:
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
                response = Response.redirect('/login')
                response.add_header('Set-Cookie', 'session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly')
                return response


class BaseController:
    def __init__(self, 
                 auth_manager: Optional[AuthManager] = None,
                 session_manager: Optional[SessionManager] = None,
                 template_dir: str = "templates"):
        self.auth = auth_manager or AuthManager()
        self.sessions = session_manager or SessionManager()
        self.template_dir = Path(template_dir)

    def get_current_user(self, request: Request) -> Optional[Dict]:
        return request.user if hasattr(request, 'user') else None

    def login_user(self, request: Request, user_data: Dict) -> Response:
        session_id = self.sessions.create_session({'user': user_data})
        response = Response.redirect('/dashboard')
        response.add_header('Set-Cookie', f'session_id={session_id}; Path=/; HttpOnly')
        return response

    def logout_user(self, request: Request) -> Response:
        if session_id := request.cookies.get('session_id'):
            self.sessions.destroy_session(session_id)
        response = Response.redirect('/login')
        response.add_header('Set-Cookie', 'session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
        return response

    def render_template(self, template_name: str, 
                       context: Dict[str, Any] = None) -> Response:
        template_path = self.template_dir / template_name
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if context:
                    content = content.format(**context)
                return Response.html(content)
        except FileNotFoundError:
            return Response.html("Template não encontrado", 404)

    def process_form(self, form_class: Type[Form], 
                    request: Request) -> Tuple[Form, bool]:
        form_data = self._extract_form_data(request)
        form = form_class(form_data)
        is_valid = form.validate()
        return form, is_valid

    def _extract_form_data(self, request: Request) -> Dict:
        if request.body is None:
            return {}
            
        if isinstance(request.body, dict):
            return {k: v[0] if isinstance(v, list) else v 
                    for k, v in request.body.items()}
                    
        return {}

    def redirect(self, url: str, status_code: int = 302) -> Response:
        return Response.redirect(url, status_code)

    def json_response(self, data: Any, status_code: int = 200) -> Response:
        return Response.json(data, status_code)

    def handle_error(self, message: str, 
                    status_code: int = 500) -> Response:
        return self.render_template(
            'error.html',
            {'error': message, 'status_code': status_code},
            status_code
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return kwargs