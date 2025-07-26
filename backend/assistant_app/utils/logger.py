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
            "details": details or {}
        }
        self.logger.info(f"User action: {json.dumps(log_data)}")

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log errors with context."""
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        self.logger.error(f"Error: {json.dumps(log_data)}")

    def log_info(self, message: str, context: Dict[str, Any] = None):
        """Log informational messages."""
        log_data = {
            "message": message,
            "context": context or {}
        }
        self.logger.info(f"Info: {json.dumps(log_data)}")

    def log_debug(self, message: str, context: Dict[str, Any] = None):
        """Log debug messages."""
        log_data = {
            "message": message,
            "context": context or {}
        }
        self.logger.debug(f"Debug: {json.dumps(log_data)}")

    def log_warning(self, message: str, context: Dict[str, Any] = None):
        """Log warning messages."""
        log_data = {
            "message": message,
            "context": context or {}
        }
        self.logger.warning(f"Warning: {json.dumps(log_data)}")

# Global logger instances
auth_logger = StructuredLogger("auth")
user_logger = StructuredLogger("user")
error_logger = StructuredLogger("error")
chat_logger = StructuredLogger("chat")
task_logger = StructuredLogger("task")
gmail_logger = StructuredLogger("gmail")
webhook_logger = StructuredLogger("webhook")
streamlit_logger = StructuredLogger("streamlit")
memory_logger = StructuredLogger("memory")
agent_logger = StructuredLogger("agent")
