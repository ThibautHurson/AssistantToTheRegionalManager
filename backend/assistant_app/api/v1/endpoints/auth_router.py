import os
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.assistant_app.api_integration.db import get_db
from backend.assistant_app.models.user import User
from backend.assistant_app.models.task import Task
from backend.assistant_app.services.auth_service import auth_service
from backend.assistant_app.services.user_data_service import UserDataService
from backend.assistant_app.utils.logger import error_logger

router = APIRouter(prefix="/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        error_logger.log_info("Registration attempt", {"email": request.email})
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            error_logger.log_warning("Registration failed - user already exists", {"email": request.email})
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create new user using AuthService
        success, message = auth_service.register_user(request.email, request.password)
        
        if success:
            error_logger.log_info("Registration successful", {"email": request.email})
            return {"message": message}
        else:
            error_logger.log_warning("Registration failed", {"email": request.email, "message": message})
            raise HTTPException(status_code=400, detail=message)
        
    except HTTPException:
        raise
    except Exception as e:
        error_logger.log_error(e, {"context": "register", "email": request.email})
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return session token."""
    try:
        error_logger.log_info("Login attempt", {"email": request.email})
        # Use AuthService for login
        session_token, message = auth_service.login_user(request.email, request.password)
        
        if session_token:
            # Get user info for response
            user = db.query(User).filter(User.email == request.email).first()
            response_data = {
                "session_token": session_token,
                "user_email": user.email
            }
            error_logger.log_info("Login successful", {"user_email": user.email, "session_token": session_token[:10] + "..."})
            return response_data
        else:
            error_logger.log_warning("Login failed", {"user_email": request.email, "message": message})
            raise HTTPException(status_code=401, detail=message)
        
    except HTTPException:
        raise
    except Exception as e:
        error_logger.log_error(e, {"context": "login", "email": request.email})
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/logout")
async def logout(session_token: str = None):
    """Logout user and invalidate session."""
    if not session_token:
        error_logger.log_warning("Logout attempt without session token")
        raise HTTPException(status_code=400, detail="Session token required")
    
    try:
        error_logger.log_info("Logout attempt", {"session_token": session_token[:10] + "..."})
        success = auth_service.logout_user(session_token)
        if success:
            error_logger.log_info("Logout successful", {"session_token": session_token[:10] + "..."})
            return {"message": "Logged out successfully"}
        else:
            error_logger.log_warning("Logout failed - invalid session token", {"session_token": session_token[:10] + "..."})
            raise HTTPException(status_code=400, detail="Invalid session token")
    except HTTPException:
        raise
    except Exception as e:
        error_logger.log_error(e, {"context": "logout", "session_token": session_token[:10] + "..."})
        raise HTTPException(status_code=500, detail="Logout failed")

@router.post("/validate_session")
async def validate_session(session_token: str = None):
    """Validate session token and return user info."""
    if not session_token:
        error_logger.log_warning("Session validation attempt without session token")
        raise HTTPException(status_code=400, detail="Session token required")
    
    try:
        error_logger.log_info("Session validation attempt", {"session_token": session_token[:10] + "..."})
        user = auth_service.validate_session(session_token)
        if not user:
            error_logger.log_warning("Session validation failed - invalid session", {"session_token": session_token[:10] + "..."})
            raise HTTPException(status_code=401, detail="Invalid session")
        
        error_logger.log_info("Session validation successful", {"user_email": user.email})
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "oauth_authenticated": user.is_oauth_authenticated
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        error_logger.log_error(e, {"context": "validate_session", "session_token": session_token[:10] + "..."})
        raise HTTPException(status_code=500, detail="Session validation failed")

@router.delete("/user-data")
async def clear_user_data(session_token: str = None, db: Session = Depends(get_db)):
    """Clear all user data including tasks, chat history, and OAuth credentials."""
    if not session_token:
        error_logger.log_warning("User data clear attempt without session token")
        raise HTTPException(status_code=400, detail="Session token required")
    
    try:
        error_logger.log_info("User data clear attempt", {"session_token": session_token[:10] + "..."})
        # Validate session
        user = auth_service.validate_session(session_token)
        if not user:
            error_logger.log_warning("User data clear failed - invalid session", {"session_token": session_token[:10] + "..."})
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Clear user data
        user_data_service = UserDataService()
        result = user_data_service.clear_user_data(user.email)
        
        error_logger.log_info("User data cleared successfully", {"user_email": user.email, "result": result})
        return {
            "message": "User data cleared successfully",
            "details": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_logger.log_error(e, {"context": "clear_user_data", "user_email": user.email if 'user' in locals() else None})
        raise HTTPException(status_code=500, detail="Failed to clear user data")
