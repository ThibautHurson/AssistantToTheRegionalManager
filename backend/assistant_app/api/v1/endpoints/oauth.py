from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from backend.assistant_app.api_integration.google_token_store import (
    get_authorization_url, exchange_code_for_token, load_credentials
)

router = APIRouter()

@router.get("/authorize")
async def authorize(session_id: str):
    print('in authorize')
    try:
        if not session_id:
            print("No session_id provided")
            return JSONResponse(content={"error": "No session_id provided"}, status_code=400)
            
        print(f"Checking credentials for session_id: {session_id}")
        existing = load_credentials(session_id)
        if existing and existing.valid:
            print("User already authenticated")
            return JSONResponse(content={"message": "Already authenticated"}, status_code=200)
        
        print("Generating authorization URL...")
        try:
            auth_url, flow = get_authorization_url(session_id)
        except FileNotFoundError as e:
            print(f"Client secret file not found: {e}")
            return JSONResponse(
                content={"error": "OAuth configuration error. Please ensure the client secret file is properly set up."},
                status_code=500
            )
        except Exception as e:
            print(f"Error generating auth URL: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
            
        if auth_url is None:  # This means we're already authenticated
            print("Already authenticated (from get_authorization_url)")
            return JSONResponse(content={"message": "Already authenticated"}, status_code=200)
            
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
    
    if not code:
        return JSONResponse({"error": "Missing code"}, status_code=400)

    creds = exchange_code_for_token(code, state)
    return JSONResponse({"message": "Authenticated"})