import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import bcrypt
from backend.assistant_app.models.user import User
from backend.assistant_app.models.user_session import UserSession
from backend.assistant_app.api_integration.db import get_db
from backend.assistant_app.utils.logger import auth_logger


class AuthService:
    def __init__(self):
        self.session_duration = timedelta(hours=24)  # 24 hour sessions

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

    def register_user(self, email: str, password: str) -> Tuple[bool, str]:
        """Register a new user."""
        db = next(get_db())
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                auth_logger.log_auth_event("register", email, False, 
                                        details={"reason": "user_exists"})
                return False, "User with this email already exists"

            # Create new user
            password_hash = self.hash_password(password)
            user = User(
                email=email,
                password_hash=password_hash
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            auth_logger.log_auth_event("register", email, True, 
                                    details={"user_id": user.id})
            return True, "User registered successfully"
        finally:
            db.close()

    def login_user(self, email: str, password: str) -> Tuple[Optional[str], str]:
        """Login a user and return session token."""
        db = next(get_db())
        try:
            # Find user
            user = db.query(User).filter(User.email == email).first()
            if not user:
                auth_logger.log_auth_event("login", email, False, 
                                        details={"reason": "user_not_found"})
                return None, "Invalid email or password"

            # Verify password
            if not self.verify_password(password, user.password_hash):
                auth_logger.log_auth_event("login", email, False, 
                                        details={"reason": "invalid_password"})
                return None, "Invalid email or password"

            # Create session
            session_token = self.generate_session_token()
            expires_at = datetime.utcnow() + self.session_duration

            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                expires_at=expires_at
            )

            # Update last login
            user.last_login = datetime.utcnow()

            db.add(user_session)
            db.commit()

            auth_logger.log_auth_event("login", email, True, 
                                    details={"user_id": user.id, 
                                           "session_token": session_token[:10] + "..."})
            return session_token, "Login successful"
        finally:
            db.close()

    def validate_session(self, session_token: str) -> Optional[User]:
        """Validate a session token and return the user."""
        db = next(get_db())
        try:
            session = db.query(UserSession).filter(
                UserSession.session_token == session_token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).first()

            if not session:
                return None

            # Update last activity
            session.last_activity = datetime.utcnow()
            db.commit()

            return session.user
        finally:
            db.close()

    def logout_user(self, session_token: str) -> bool:
        """Logout a user by deactivating their session."""
        db = next(get_db())
        try:
            session = db.query(UserSession).filter(
                UserSession.session_token == session_token
            ).first()

            if session:
                session.is_active = False
                db.commit()
                auth_logger.log_auth_event("logout", session.user.email, True, 
                                        details={"session_token": session_token[:10] + "..."})
                return True

            return False
        finally:
            db.close()

    def update_oauth_status(self, user_id: str, is_authenticated: bool) -> bool:
        """Update user's OAuth authentication status."""
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_oauth_authenticated = is_authenticated
                db.commit()
                auth_logger.log_user_action(user.email, "oauth_status_update", 
                                         details={"is_authenticated": is_authenticated})
                return True

            return False
        finally:
            db.close()

    def get_user_session_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive session information including user details."""
        user = self.validate_session(session_token)
        if not user:
            return None

        db = next(get_db())
        try:
            session = db.query(UserSession).filter(
                UserSession.session_token == session_token
            ).first()

            return {
                "user_id": user.id,
                "email": user.email,
                "is_oauth_authenticated": user.is_oauth_authenticated,
                "session_token": session_token,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "last_activity": (session.last_activity.isoformat() 
                                if session.last_activity else None)
            }
        finally:
            db.close()


# Global instance
auth_service = AuthService()
