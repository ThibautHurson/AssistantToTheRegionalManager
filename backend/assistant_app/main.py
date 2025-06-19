from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

import backend.assistant_app.agents.tools
from backend.assistant_app.api.v1.endpoints import tool_router, chat, oauth, gmail_webhook, task_router
from backend.assistant_app.api_integration.google_token_store import load_credentials
from backend.assistant_app.api_integration.db import engine
from backend.assistant_app.models.task import Base


load_dotenv()
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_TOPIC = os.getenv("GOOGLE_TOPIC")
SESSION_ID = os.getenv("SESSION_ID")


app = FastAPI()

# Create database tables
Base.metadata.create_all(bind=engine)

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
app.include_router(task_router.router)
