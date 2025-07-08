from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from backend.assistant_app.api_integration.google_token_store import (
    get_authorization_url, exchange_code_for_token, load_credentials, clear_credentials
)
from backend.assistant_app.services.auth_service import auth_service

router = APIRouter()

@router.get("/authorize")
async def authorize(session_token: str):
    print('in authorize')
    try:
        if not session_token:
            print("No session_token provided")
            return JSONResponse(content={"error": "No session_token provided"}, status_code=400)
            
        print(f"Checking credentials for session_token: {session_token}")
        
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            print("Invalid session token")
            return JSONResponse(content={"error": "Invalid session token"}, status_code=401)
        
        # Check if already OAuth authenticated
        if user.is_oauth_authenticated:
            existing = load_credentials(user.email)
            if existing and existing.valid:
                print("User already OAuth authenticated")
                return JSONResponse(content={"message": "Already OAuth authenticated"}, status_code=200)
        
        print("Generating authorization URL...")
        try:
            auth_url, flow = get_authorization_url(session_token)
        except FileNotFoundError as e:
            print(f"Client secret file not found: {e}")
            return JSONResponse(
                content={"error": "OAuth configuration error. Please ensure the client secret file is properly set up."},
                status_code=500
            )
        except ValueError as e:
            print(f"Invalid session token: {e}")
            return JSONResponse(content={"error": "Invalid session token"}, status_code=401)
        except Exception as e:
            print(f"Error generating auth URL: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
            
        if auth_url is None:  # This means we're already authenticated
            print("Already OAuth authenticated (from get_authorization_url)")
            return JSONResponse(content={"message": "Already OAuth authenticated"}, status_code=200)
            
        print(f"Returning auth URL: {auth_url}")
        return JSONResponse(content={"auth_url": auth_url}, status_code=200)
    except Exception as e:
        print(f"Error in authorize endpoint: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/oauth2callback")
def oauth2callback(request: Request):
    print("in oauth2callback")
    code = request.query_params.get("code")
    state = request.query_params.get("state") or "default"
    session_token = request.query_params.get("session_token")
    
    if not code:
        return JSONResponse({"error": "Missing code"}, status_code=400)
    
    if not session_token:
        return JSONResponse({"error": "Missing session_token"}, status_code=400)

    creds = exchange_code_for_token(code, state, session_token)
    if creds:
        return JSONResponse({"message": "OAuth authentication successful"})
    else:
        return JSONResponse({"error": "OAuth authentication failed"}, status_code=400)

@router.post("/oauth/clear-credentials")
async def clear_user_credentials(session_token: str):
    """Clear stored Google credentials for a user to force new OAuth flow."""
    try:
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            return JSONResponse(content={"error": "Invalid session token"}, status_code=401)
        
        # Clear credentials
        success = clear_credentials(user.email)
        if success:
            return JSONResponse(content={"message": "Credentials cleared successfully. Please re-authenticate."})
        else:
            return JSONResponse(content={"error": "Failed to clear credentials"}, status_code=500)
            
    except Exception as e:
        print(f"Error clearing credentials: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)