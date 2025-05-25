from dotenv import load_dotenv
import os
import httpx

load_dotenv()

REDIRECT_URI = os.getenv("REDIRECT_URI")
MARKTPLAATS_CLIENT_ID = os.getenv("MARKTPLAATS_CLIENT_ID")
MARKTPLAATS_CLIENT_SECRET = os.getenv("MARKTPLAATS_CLIENT_SECRET")

def exchange_code_for_token(auth_code: str):
    import base64
    import httpx
    auth_str = f"{MARKTPLAATS_CLIENT_ID}:{MARKTPLAATS_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
    }
    response = httpx.post("https://auth.marktplaats.nl/accounts/oauth/token", headers=headers, data=data)
    response.raise_for_status()
    return response.json()

