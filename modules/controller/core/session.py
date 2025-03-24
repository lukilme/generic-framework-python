import time
import uuid
from typing import Dict, Any, Optional

# Padrão Singleton
class SessionManager:
    """Gerencia sessões de usuário (implementação do padrão Singleton)."""
    
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