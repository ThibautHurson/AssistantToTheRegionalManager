from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.assistant_app.api.v1.endpoints import chat, oauth, gmail_webhook, task_router
from backend.assistant_app.api.v1.endpoints import prompt_router, auth_router

from backend.assistant_app.api_integration.db import engine, Base
#  Import all models to ensure their tables are created
from backend.assistant_app.models.task import Task
from backend.assistant_app.models.user import User
from backend.assistant_app.models.user_session import UserSession

app = FastAPI()
#  Create database tables
Base.metadata.create_all(bind=engine)
#  Add CORS middleware
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"], )

#  Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

app.include_router(chat.router)
app.include_router(oauth.router)
app.include_router(gmail_webhook.router)
app.include_router(task_router.router)
app.include_router(prompt_router.router)
app.include_router(auth_router.router)
