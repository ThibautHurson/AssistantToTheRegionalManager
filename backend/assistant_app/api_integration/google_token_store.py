import os
import json
from datetime import datetime
from typing import Optional, Tuple
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import redis
from dotenv import load_dotenv
import httpx
from backend.assistant_app.utils.redis_saver import save_to_redis
from backend.assistant_app.services.auth_service import auth_service
from backend.assistant_app.utils.logger import gmail_logger, error_logger

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
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

def handle_google_api_error(e: Exception, user_email: str, context: str = "unknown") -> bool:
    """
    Handle Google API errors and determine if credentials should be cleared.
    
    Args:
        e: The exception that occurred
        user_email: The user's email address
        context: Context where the error occurred
        
    Returns:
        bool: True if credentials should be cleared, False otherwise
    """
    error_str = str(e).lower()
    
    # Check for credential-related errors that require re-authentication
    credential_errors = [
        "invalid_grant",
        "token has been expired or revoked",
        "invalid_scope",
        "unauthorized",
        "invalid_credentials",
        "access_denied"
    ]
    
    should_clear = any(error in error_str for error in credential_errors)
    
    if should_clear:
        gmail_logger.log_warning("Google API credential error detected", {
            "user_email": user_email,
            "context": context,
            "error": str(e),
            "error_type": "credential_error"
        })
        
        # Clear credentials
        clear_credentials(user_email)
        
        # Update user's OAuth status to False
        try:
            user = auth_service.get_user_by_email(user_email)
            if user:
                auth_service.update_oauth_status(user.id, False)
        except Exception as auth_error:
            error_logger.log_error(auth_error, {
                "context": "update_oauth_status_after_api_error",
                "user_email": user_email
            })
    
    return should_clear

def load_client_config():
    """Load OAuth2 client configuration from file."""
    if not os.path.exists(CLIENT_SECRET_FILE):
        gmail_logger.log_warning("Client secret file not found", {
            "file_path": CLIENT_SECRET_FILE
        })
        return None

    with open(CLIENT_SECRET_FILE, 'r') as f:
        return json.load(f)

def clear_credentials(user_email: str) -> bool:
    """Clear stored credentials for a user to force new OAuth flow."""
    try:
        # Clear from Redis
        redis_client.delete(f"google_creds:{user_email}")

        # Clear from file backup
        file_path = f'google_setup/token_store/{user_email}.json'
        if os.path.exists(file_path):
            os.remove(file_path)
            gmail_logger.log_info("Cleared credentials", {"user_email": user_email})
            return True
    except Exception as e:
        error_logger.log_error(e, {
            "context": "clear_credentials",
            "user_email": user_email
        })
        return False
    return True

def load_credentials(user_email: str) -> Optional[Credentials]:
    gmail_logger.log_debug("Loading credentials", {"user_email": user_email})
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
            gmail_logger.log_warning("No credentials found", {"user_email": user_email})
            return None

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
    # Restore expiry if present
    if 'expiry' in creds_dict and creds_dict['expiry']:
        creds.expiry = datetime.fromisoformat(creds_dict['expiry'])

    if creds and creds.expired and creds.refresh_token:
        gmail_logger.log_info("Credentials expired, refreshing", {"user_email": user_email})
        try:
            creds.refresh(Request())
            save_credentials(user_email, creds)
            # Set up Gmail watch after refreshing credentials, passing the refreshed creds
            setup_gmail_watch(user_email, creds)
        except Exception as e:
            error_logger.log_error(e, {"context": "refresh_token", "user_email": user_email})
            # Use the centralized error handler
            handle_google_api_error(e, user_email, "refresh_token")
            return None
    gmail_logger.log_debug("Returning credentials", {"user_email": user_email})
    return creds if creds and creds.valid else None

def save_credentials(user_email: str, creds: Credentials):
    gmail_logger.log_debug("Saving credentials to Redis", {"user_email": user_email})
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


def get_authorization_url(session_token: str) -> Tuple[Optional[str], Optional[Flow]]:
    """
    Get the authorization URL for Google OAuth2 flow.
    Returns a tuple of (auth_url, flow) or (None, None) if already authenticated.
    """
    gmail_logger.log_debug("Getting authorization URL", {
        "session_token": session_token[:10] + "..."
    })
    # First check if we already have valid credentials for this user
    user = auth_service.validate_session(session_token)
    if not user:
        raise ValueError("Invalid session token")

    existing = load_credentials(user.email)
    if existing and existing.valid:
        gmail_logger.log_info("Valid credentials found", {"user_email": user.email})
        return None, None

    # Load client configuration
    client_config = load_client_config()
    if not client_config:
        gmail_logger.log_error("No client configuration found", {"user_email": user.email})
        raise FileNotFoundError("Client secret file not found or invalid")

    # Create Flow instance with explicit redirect URI that includes session_token
    redirect_uri_with_token = f"{REDIRECT_URI}?session_token={session_token}"

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri_with_token
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
        gmail_logger.log_info("Setting up Gmail watch", {"email": email})
        if not creds:
            creds = load_credentials(email)
        if not creds:
            gmail_logger.log_warning("No valid credentials found", {"email": email})
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

        gmail_logger.log_info("Watch response received", {"response": watch_response})
        return True
    except Exception as e:
        error_logger.log_error(e, {"context": "setup_gmail_watch", "email": email})
        return False

def exchange_code_for_token(code: str, state: str, session_token: str) -> Optional[Credentials]:
    """Exchange authorization code for access token."""
    gmail_logger.log_debug("Exchanging code for token", {
        "session_token": session_token[:10] + "..."
    })
    try:
        # Validate session and get user
        user = auth_service.validate_session(session_token)
        if not user:
            gmail_logger.log_warning("Invalid session token", {
                "session_token": session_token[:10] + "..."
            })
            return None

        # Load client configuration
        client_config = load_client_config()
        if not client_config:
            gmail_logger.log_error("No client configuration found", {
                "session_token": session_token[:10] + "..."
            })
            return None

        # Create Flow instance with explicit redirect URI that includes session_token
        redirect_uri_with_token = f"{REDIRECT_URI}?session_token={session_token}"

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri_with_token
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        # Get user email from ID token
        id_token = creds.id_token
        if not id_token:
            gmail_logger.log_warning("No ID token found in credentials", {
                "user_email": user.email
            })
            return None

        # Decode the JWT token
        import jwt
        try:
            # Decode without verification since we trust Google's token
            decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            oauth_email = decoded_token.get('email')
            if not oauth_email:
                gmail_logger.log_warning("No email found in ID token", {
                    "user_email": user.email
                })
                return None

            gmail_logger.log_info("Found email in ID token", {
                "oauth_email": oauth_email,
                "user_email": user.email
            })

            # Verify the OAuth email matches the user's email
            if oauth_email != user.email:
                gmail_logger.log_warning("OAuth email doesn't match user email", {
                    "oauth_email": oauth_email,
                    "user_email": user.email
                })
                return None

            # Save credentials using user email
            save_credentials(user.email, creds)

            # Update user's OAuth status
            auth_service.update_oauth_status(user.id, True)

            return creds
        except Exception as e:
            error_logger.log_error(e, {
                "context": "decode_id_token",
                "user_email": user.email
            })
            return None

    except Exception as e:
        error_logger.log_error(e, {
            "context": "exchange_code_for_token",
            "session_token": session_token[:10] + "..."
        })
        return None

def fetch_user_email(creds):
    headers = {
        "Authorization": f"Bearer {creds.token}"
    }

    resp = httpx.get("https://www.googleapis.com/oauth2/v3/userinfo",
                     headers=headers,
                     timeout=10)
    resp.raise_for_status()
    return resp.json()["email"]
