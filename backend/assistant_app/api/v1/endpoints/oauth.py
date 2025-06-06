from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from backend.assistant_app.api_integration.google_token_store import (
    get_authorization_url, exchange_code_for_token, load_credentials, fetch_user_email
)

router = APIRouter()

@router.get("/authorize")
async def authorize(session_id: str):
    print('in authorize')
    try:
        existing = load_credentials(session_id)
        if existing:
            return JSONResponse(content={"message": "Already authenticated"}, status_code=200)
        
        auth_url, _ = get_authorization_url(session_id)
        return RedirectResponse(auth_url)
    except Exception as e:
        print(f"Error in authorize endpoint: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/oauth2callback")
def oauth2callback(request: Request):
    print("in oauth2callback")
    code = request.query_params.get("code")
    state = request.query_params.get("state") or "default"
    
    if not code:
        return JSONResponse({"error": "Missing code"}, status_code=400)

    creds = exchange_code_for_token(code)
    return JSONResponse({"message": "Authenticated"})