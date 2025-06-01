import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
# from dotenv import load_dotenv
import redis
import uuid
from backend.assistant_app.api_integration.google_token_store import get_google_credencials
import backend.assistant_app.agents.tools
from backend.assistant_app.api.v1.endpoints import tool_router

app = FastAPI()

app.include_router(tool_router.router)

redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
r = redis.Redis.from_url(redis_url)