import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.assistant_app.services.auth_service import auth_service
from backend.assistant_app.api_integration.google_token_store import (
    get_authorization_url, exchange_code_for_token, clear_credentials
)
from backend.assistant_app.utils.logger import auth_logger, error_logger

router = APIRouter()

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str

@router.get("/authorize")
async def authorize(session_token: str = None):
    """Generate OAuth authorization URL."""
    auth_logger.log_debug("Authorize endpoint called", {"session_token": session_token})

    if not session_token:
        auth_logger.log_warning("No session_token provided")
        raise HTTPException(status_code=400, detail="Session token required")

    try:
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            auth_logger.log_warning("Invalid session token", {"session_token": session_token})
            raise HTTPException(status_code=401, detail="Invalid session token")

        auth_logger.log_debug("Checking credentials", {
            "session_token": session_token,
            "user_email": user.email
        })

        # Check if user is already OAuth authenticated
        if user.is_oauth_authenticated:
            auth_logger.log_info("User already OAuth authenticated", {"user_email": user.email})
            return {"message": "Already OAuth authenticated"}

        auth_logger.log_info("Generating authorization URL", {"user_email": user.email})

        # Get authorization URL
        auth_url = get_authorization_url(user.email)

        if not auth_url:
            auth_logger.log_info("Already OAuth authenticated (from get_authorization_url)", {
                "user_email": user.email
            })
            return {"message": "Already OAuth authenticated"}

        auth_logger.log_info("Returning auth URL", {
            "user_email": user.email,
            "auth_url": auth_url
        })
        return {"auth_url": auth_url}

    except FileNotFoundError as e:
        error_logger.log_error(e, {"context": "client_secret_not_found"})
        raise HTTPException(status_code=500, detail="OAuth configuration not found")
    except ValueError as e:
        error_logger.log_error(e, {"context": "invalid_session_token"})
        raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception as e:
        error_logger.log_error(e, {
            "context": "authorize_endpoint",
            "traceback": traceback.format_exc()
        })
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/oauth2callback")
async def oauth2callback(request: OAuthCallbackRequest, session_token: str = None):
    """Handle OAuth callback and exchange code for token."""
    auth_logger.log_debug("OAuth callback received", {"session_token": session_token})

    try:
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Exchange authorization code for token
        success = exchange_code_for_token(request.code, user.email)

        if success:
            # Update user's OAuth status
            auth_service.update_oauth_status(user.id, True)

            return {
                "message": "OAuth authentication successful",
                "user_email": user.email
            }
        raise HTTPException(status_code=400, detail="OAuth authentication failed")

    except Exception as e:
        error_logger.log_error(e, {"context": "oauth2callback"})
        raise HTTPException(status_code=500, detail="OAuth callback failed")

@router.post("/clear-credentials")
async def clear_user_credentials(session_token: str = None):
    """Clear OAuth credentials for the current user."""
    if not session_token:
        raise HTTPException(status_code=400, detail="Session token required")

    try:
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Clear credentials
        clear_credentials(user.email)

        # Update user's OAuth status
        auth_service.update_oauth_status(user.id, False)
        
        return {"message": "Credentials cleared successfully"}

    except Exception as e:
        error_logger.log_error(e, {"context": "clear_credentials"})
        raise HTTPException(status_code=500, detail="Failed to clear credentials")
