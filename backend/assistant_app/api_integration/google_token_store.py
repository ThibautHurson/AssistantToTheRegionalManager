import os
from typing import Optional
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import httpx

load_dotenv()

CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_JSON", "google_setup/credentials.json")
SCOPES = [
    "openid",             # Required for ID token
    "https://www.googleapis.com/auth/userinfo.email",  
    "https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = os.getenv("REDIRECT_URI")  # e.g., http://localhost:8000/oauth2callback
TOKEN_DIR = "google_setup/token_store"

os.makedirs(TOKEN_DIR, exist_ok=True)

def _token_path(user_id: str) -> str:
    return os.path.join(TOKEN_DIR, f"{user_id}.json")


def load_credentials(user_id: str) -> Optional[Credentials]:
    print("in load_credentials")
    path = _token_path(user_id)
    if not os.path.exists(path):
        print("Path not found")
        return None

    creds = Credentials.from_authorized_user_file(path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("Credentials expired. Need to refresh")

        try:
            creds.refresh(Request())
            save_credentials(user_id, creds)
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    print("load_credentials Returning credencials")
    return creds if creds and creds.valid else None


def save_credentials(user_id: str, creds: Credentials):
    print("Saving credentials")
    print(f"Credencials being saved at path: {_token_path(user_id)}")
    with open(_token_path(user_id), "w") as f:
        f.write(creds.to_json())


def get_authorization_url(user_id: str):
    creds = load_credentials(user_id)
    print("load_credentials returned creds")
    if creds and creds.valid:
        print(f"Credentials valid: {creds.valid}")
        return None  # Already authenticated

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        prompt='consent',
        access_type='offline',
        include_granted_scopes='true',
    )
    # Save flow state in memory or session if needed
    return auth_url, flow


def exchange_code_for_token(code: str):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    user_id = fetch_user_email(creds)
    save_credentials(user_id, creds)
    return creds


def fetch_user_email(creds):
    headers = {
        "Authorization": f"Bearer {creds.token}"
    }

    resp = httpx.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()["email"]