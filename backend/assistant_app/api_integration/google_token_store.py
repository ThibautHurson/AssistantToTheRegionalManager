import os
import json
from typing import Optional, Tuple
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import redis
from dotenv import load_dotenv
import httpx
from backend.assistant_app.utils.redis_saver import save_to_redis
from datetime import datetime
from backend.assistant_app.services.auth_service import auth_service
load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis-aof")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = 'True'

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# Google OAuth2 configuration
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "google_setup/client_secret.json")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth2callback")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_TOPIC = os.getenv("GOOGLE_TOPIC")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send"
]

def load_client_config():
    """Load OAuth2 client configuration from file."""
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"Client secret file not found at {CLIENT_SECRET_FILE}")
        return None

    with open(CLIENT_SECRET_FILE, 'r') as f:
        return json.load(f)

def load_credentials(user_email: str) -> Optional[Credentials]:
    print("in load_credentials")
    # Try Redis first
    creds_json = redis_client.get(f"google_creds:{user_email}")
    
    # If not in Redis, try file backup
    if not creds_json:
        try:
            with open(f'google_setup/token_store/{user_email}.json', 'r') as f:
                creds_json = f.read()
                # Restore to Redis
                redis_client.set(f"google_creds:{user_email}", creds_json)
        except FileNotFoundError:
            print("No credentials found in Redis or file backup")
            return None

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
    # Restore expiry if present
    if 'expiry' in creds_dict and creds_dict['expiry']:
        creds.expiry = datetime.fromisoformat(creds_dict['expiry'])

    if creds and creds.expired and creds.refresh_token:
        print("Credentials expired. Need to refresh")
        try:
            creds.refresh(Request())
            save_credentials(user_email, creds)
            # Set up Gmail watch after refreshing credentials, passing the refreshed creds
            setup_gmail_watch(user_email, creds)
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    print("load_credentials Returning credentials")
    return creds if creds and creds.valid else None

def save_credentials(user_email: str, creds: Credentials):
    print("Saving credentials to Redis")
    creds_dict = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes,
        'expiry': creds.expiry.isoformat() if creds.expiry else None
    }
    # Save to Redis
    redis_client.set(f"google_creds:{user_email}", json.dumps(creds_dict))
    
    # Backup to file
    os.makedirs('google_setup/token_store', exist_ok=True)
    with open(f'google_setup/token_store/{user_email}.json', 'w') as f:
        json.dump(creds_dict, f)

def save_to_redis(key: str, field: str, value: str):
    """Save a value to Redis with a key and field."""
    redis_client.set(f"{key}:{field}", value)

def get_authorization_url(session_token: str) -> Tuple[Optional[str], Optional[Flow]]:
    """
    Get the authorization URL for Google OAuth2 flow.
    Returns a tuple of (auth_url, flow) or (None, None) if already authenticated.
    """
    print("in get_authorization_url")
    # First check if we already have valid credentials for this user
    user = auth_service.validate_session(session_token)
    if not user:
        raise ValueError("Invalid session token")
    
    existing = load_credentials(user.email)
    if existing and existing.valid:
        print("Valid credentials found")
        return None, None

    # Load client configuration
    client_config = load_client_config()
    if not client_config:
        print("No client configuration found")
        raise FileNotFoundError("Client secret file not found or invalid")

    # Create Flow instance with explicit redirect URI
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI  # Use the environment variable
    )

    # Generate authorization URL
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"  # Force consent screen to ensure all scopes are granted
    )

    # Store state in Redis for verification
    save_to_redis(user.email, "oauth_state", state)

    return auth_url, flow

def setup_gmail_watch(email: str, creds: Optional[Credentials] = None) -> bool:
    """Set up Gmail watch notifications for the user's inbox.
    
    Args:
        email: The user's email address
        creds: Optional credentials to use. If not provided, will load them.
        
    Returns:
        bool: True if watch was set up successfully, False otherwise
    """
    try:
        print(f"Setting up Gmail watch for {email}")
        if not creds:
            creds = load_credentials(email)
        if not creds:
            print(f"No valid credentials found for {email}")
            return False
            
        service = build("gmail", "v1", credentials=creds)
        
        # Set up watch
        watch_response = service.users().watch(
            userId='me',
            body={
                'labelIds': ['INBOX'],
                'topicName': f'projects/{GOOGLE_PROJECT_ID}/topics/{GOOGLE_TOPIC}'
            }
        ).execute()
        
        print(f"Watch response: {watch_response}")
        return True
    except Exception as e:
        print(f"Error setting up Gmail watch: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def exchange_code_for_token(code: str, state: str, session_token: str) -> Optional[Credentials]:
    """Exchange authorization code for access token."""
    print("in exchange_code_for_token")
    try:
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            print("Invalid session token")
            return None
        
        # Load client configuration
        client_config = load_client_config()
        if not client_config:
            print("No client configuration found")
            return None

        # Create Flow instance with explicit redirect URI
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI  # Use the environment variable
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        # Get user email from ID token
        id_token = creds.id_token
        if not id_token:
            print("No ID token found in credentials")
            return None

        # Decode the JWT token
        import jwt
        try:
            # Decode without verification since we trust Google's token
            decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            oauth_email = decoded_token.get('email')
            if not oauth_email:
                print("No email found in ID token")
                return None

            print(f"Found email in ID token: {oauth_email}")
            
            # Verify the OAuth email matches the user's email
            if oauth_email != user.email:
                print(f"OAuth email {oauth_email} doesn't match user email {user.email}")
                return None
            
            # Save credentials using user email
            save_credentials(user.email, creds)
            
            # Update user's OAuth status
            auth_service.update_oauth_status(user.id, True)
            
            return creds
        except Exception as e:
            print(f"Error decoding ID token: {e}")
            return None

    except Exception as e:
        print(f"Error exchanging code for token: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def fetch_user_email(creds):
    headers = {
        "Authorization": f"Bearer {creds.token}"
    }

    resp = httpx.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()["email"]