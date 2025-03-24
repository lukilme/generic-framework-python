import time
import uuid
from typing import Optional, Dict, List, Any, Callable, Tuple, Type
from .request import Request
from .response import Response
class SessionManager:

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance.sessions = {}
            cls._instance.session_timeout = 1800 
        return cls._instance
    
    def create_session(self, user_data: Dict[str, Any] = None) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'data': user_data or {},
            'created_at': time.time(),
            'last_access': time.time()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            if time.time() - session['last_access'] > self.session_timeout:
                self.destroy_session(session_id)
                return None
            
            session['last_access'] = time.time()
            return session['data']
        
        return None
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id]['data'].update(data)
            self.sessions[session_id]['last_access'] = time.time()
            return True
        return False
    
    def destroy_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
      
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session['last_access'] > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            self.destroy_session(session_id)

class SessionMiddleware:
    def __init__(self, cookie_name='session_id'):
        self.session_manager = SessionManager()
        self.cookie_name = cookie_name
    
    def process_request(self, request: Request):

        request.session = None
        request.user = None
        
        cookies = {}
        cookie_header = request.environ.get('HTTP_COOKIE', '')
        
        for cookie in cookie_header.split(';'):
            if '=' in cookie.strip():  
                name, value = cookie.strip().split('=', 1)
                cookies[name] = value
        
        session_id = cookies.get(self.cookie_name)
        
        if session_id:
            session_data = self.session_manager.get_session(session_id)
            request.session = session_data
            if session_data and 'user' in session_data:
                request.user = session_data.get('user')
        
        return request
    
    def process_response(self, request: Request, response: Response) -> Response:
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