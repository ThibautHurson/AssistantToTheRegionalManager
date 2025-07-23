from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.assistant_app.services.auth_service import auth_service
from backend.assistant_app.models.user import User

router = APIRouter()

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None
    user_email: Optional[str] = None

class UserInfo(BaseModel):
    email: str
    is_oauth_authenticated: bool
    created_at: str
    last_login: Optional[str] = None

def get_current_user(session_token: str) -> User:
    """Dependency to get current authenticated user."""
    user = auth_service.validate_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user

@router.post("/auth/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    """Register a new user."""
    success, message = auth_service.register_user(user_data.email, user_data.password)

    if success:
        return AuthResponse(success=True, message=message)
    else:
        raise HTTPException(status_code=400, detail=message)

@router.post("/auth/login", response_model=AuthResponse)
async def login(user_data: UserLogin):
    """Login a user."""
    session_token, message = auth_service.login_user(user_data.email, user_data.password)

    if session_token:
        return AuthResponse(
            success=True,
            message=message,
            session_token=session_token,
            user_email=user_data.email
        )
    else:
        raise HTTPException(status_code=401, detail=message)

@router.post("/auth/logout", response_model=AuthResponse)
async def logout(session_token: str):
    """Logout a user."""
    success = auth_service.logout_user(session_token)

    if success:
        return AuthResponse(success=True, message="Logged out successfully")
    else:
        raise HTTPException(status_code=400, detail="Invalid session token")

@router.get("/auth/validate", response_model=UserInfo)
async def validate_session(session_token: str):
    """Validate a session and return user info."""
    user = auth_service.validate_session(session_token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return UserInfo(
        email=user.email,
        is_oauth_authenticated=user.is_oauth_authenticated,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None
    )

@router.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserInfo(
        email=user.email,
        is_oauth_authenticated=user.is_oauth_authenticated,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None
    )

@router.post("/auth/clear-data")
async def clear_user_data(session_token: str):
    """Clear all user data including vector store data for privacy compliance."""
    try:
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session. Please log in again."
            )

        # Get the chat agent instance and clear user data
        from backend.assistant_app.api.v1.endpoints.chat import get_chat_agent
        chat_agent = get_chat_agent()
        results = chat_agent.clear_user_data(user.email)

        if results["success"]:
            return {
                "message": "User data cleared successfully",
                "details": {
                    "vector_store_cleared": results["vector_store_cleared"],
                    "redis_keys_deleted": results["redis_keys_deleted"],
                    "database_tasks_deleted": results["database_tasks_deleted"]
                }
            }
        else:
            return {
                "message": "User data cleared with some errors",
                "details": {
                    "vector_store_cleared": results["vector_store_cleared"],
                    "redis_keys_deleted": results["redis_keys_deleted"],
                    "database_tasks_deleted": results["database_tasks_deleted"],
                    "errors": results["errors"]
                }
            }
    except HTTPException:
        # Re-raise HTTPExceptions as-is (like 401 for invalid session)
        raise
    except Exception as e:
        print(f"Error clearing user data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing user data: {str(e)}"
        )