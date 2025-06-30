import logging
import json
from datetime import datetime
from typing import Dict, Any
import os

class StructuredLogger:
    """Structured logging utility for the assistant application."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for production
        if os.getenv("ENVIRONMENT") == "production":
            file_handler = logging.FileHandler("app.log")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_auth_event(self, event_type: str, user_email: str, success: bool, 
                      ip_address: str = None, details: Dict[str, Any] = None):
        """Log authentication events."""
        log_data = {
            "event_type": event_type,
            "user_email": user_email,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": ip_address,
            "details": details or {}
        }
        self.logger.info(f"Auth event: {json.dumps(log_data)}")
    
    def log_user_action(self, user_email: str, action: str, 
                       resource: str = None, details: Dict[str, Any] = None):
        """Log user actions for audit trail."""
        log_data = {
            "user_email": user_email,
            "action": action,
            "resource": resource,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        self.logger.info(f"User action: {json.dumps(log_data)}")
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log errors with context."""
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        self.logger.error(f"Error: {json.dumps(log_data)}")

# Global logger instances
auth_logger = StructuredLogger("auth")
user_logger = StructuredLogger("user")
error_logger = StructuredLogger("error") 