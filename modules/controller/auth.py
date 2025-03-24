from functools import wraps
from .response import Response
from typing import Optional, Dict, List, Any, Callable, Tuple, Type

class AuthManager:    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthManager, cls).__new__(cls)
            cls._instance.users = {}
            cls._instance.roles = {}
        return cls._instance
    
    def register_user(self, username: str, password: str, roles: List[str] = None):
        # Em produção, a senha deve ser armazenada com hash e salt
        self.users[username] = {
            'password': password,
            'roles': roles or []
        }
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        if username in self.users and self.users[username]['password'] == password:
            user_data = {
                'username': username,
                'roles': self.users[username]['roles']
            }
            return user_data
        return None
    
    def has_role(self, user_data: Dict[str, Any], role: str) -> bool:
        if user_data and 'roles' in user_data:
            return role in user_data['roles']
        return False


def require_auth(role=None):
    def decorator(handler):
        @wraps(handler)
        def wrapper(request, *args, **kwargs):
            if not request.user:
                return Response.redirect('/login')
            if role and role not in request.user.get('roles', []):
                return Response.json({"error": "Forbidden"}, 403)
            return handler(request, *args, **kwargs)
        return wrapper
    return decorator