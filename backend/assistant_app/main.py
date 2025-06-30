from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from backend.assistant_app.api.v1.endpoints import chat, oauth, gmail_webhook, task_router, prompt_router, auth_router
from backend.assistant_app.api_integration.db import engine, Base

# Import all models to ensure their tables are created
from backend.assistant_app.models.task import Task
from backend.assistant_app.models.user import User
from backend.assistant_app.models.user_session import UserSession


load_dotenv()
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_TOPIC = os.getenv("GOOGLE_TOPIC")


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

app.include_router(chat.router)
app.include_router(oauth.router)
app.include_router(gmail_webhook.router)
app.include_router(task_router.router)
app.include_router(prompt_router.router)
app.include_router(auth_router.router)
