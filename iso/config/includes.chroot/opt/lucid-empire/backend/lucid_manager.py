# LUCID EMPIRE :: BACKEND MANAGER
# Purpose: Manage backend state and lifecycle

import logging
from typing import Dict, Optional
from backend.lucid_api import LucidAPI

class BackendManager:
    """Manage backend lifecycle and state"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api = LucidAPI()
        self.active_sessions = {}
    
    def start_session(self, profile_id: str) -> Optional[str]:
        """Start new operational session"""
        profile = self.api.get_profile(profile_id)
        if profile:
            session_id = f"session_{profile_id}"
            self.active_sessions[session_id] = {'profile': profile, 'status': 'active'}
            return session_id
        return None
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get session status"""
        return self.active_sessions.get(session_id)
    
    def end_session(self, session_id: str) -> bool:
        """End operational session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    def get_active_sessions(self) -> Dict:
        """Get all active sessions"""
        return self.active_sessions.copy()
