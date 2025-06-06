from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from dotenv import load_dotenv

import backend.assistant_app.agents.tools
from backend.assistant_app.api.v1.endpoints import tool_router, chat, oauth

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