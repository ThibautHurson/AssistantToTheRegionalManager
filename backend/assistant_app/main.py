from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

import backend.assistant_app.agents.tools
from backend.assistant_app.api.v1.endpoints import tool_router, chat, oauth, gmail_webhook
from backend.assistant_app.api_integration.google_token_store import load_credentials


load_dotenv()
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_TOPIC = os.getenv("GOOGLE_TOPIC")
SESSION_ID = os.getenv("SESSION_ID")

SCOPES = [
    "openid",             # Required for ID token
    "https://www.googleapis.com/auth/userinfo.email",  
    "https://www.googleapis.com/auth/gmail.readonly"]

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tool_router.router)
app.include_router(chat.router)
app.include_router(oauth.router)
app.include_router(gmail_webhook.router)

@app.on_event("startup")
async def setup_gmail_watch():
    creds = load_credentials(SESSION_ID)
    service = build("gmail", "v1", credentials=creds)
    
    # Replace this with your actual topic
    topic_name = f"projects/{GOOGLE_PROJECT_ID}/topics/{GOOGLE_TOPIC}"

    # Set up watch on inbox
    request = {
        "labelIds": ["INBOX"],
        "topicName": topic_name
    }
    response = service.users().watch(userId="me", body=request).execute()
    print("Gmail watch response:", response)
