# LUCID EMPIRE :: BACKEND COMMANDER
# Purpose: Command and control interface for operations

import logging
from typing import Dict, Optional

class CommandInterface:
    """Command and control interface"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.command_queue = []
        self.response_handlers = {}
    
    def queue_command(self, cmd: Dict) -> str:
        """Queue a command for execution"""
        cmd_id = f"cmd_{len(self.command_queue)}"
        self.command_queue.append({'id': cmd_id, 'cmd': cmd})
        return cmd_id
    
    def get_next_command(self) -> Optional[Dict]:
        """Get next command from queue"""
        return self.command_queue.pop(0) if self.command_queue else None
    
    def register_handler(self, cmd_type: str, handler: callable) -> None:
        """Register command handler"""
        self.response_handlers[cmd_type] = handler
    
    def handle_response(self, cmd_type: str, response: Dict) -> None:
        """Handle command response"""
        handler = self.response_handlers.get(cmd_type)
        if handler:
            handler(response)
