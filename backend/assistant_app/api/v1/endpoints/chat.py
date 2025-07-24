import json
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.assistant_app.agents.mistral_chat_agent import MistralMCPChatAgent
from backend.assistant_app.api_integration.google_token_store import load_credentials
from backend.assistant_app.services.auth_service import auth_service

with open("backend/assistant_app/configs/chat_config.json") as f:
    config = json.load(f)


# Path to your MCP server script
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "backend/assistant_app/mcp_server.py")

# Create the agent globally (not connected yet)
agent = MistralMCPChatAgent(config=config)

# FastAPI router
router = APIRouter()

def get_chat_agent() -> MistralMCPChatAgent:
    return agent

@router.on_event("startup")
async def startup_event():
    await agent.connect_to_server(MCP_SERVER_PATH)
    await agent.connect_to_fetch_server()

class ChatRequest(BaseModel):
    input: str
    session_token: str
    chat_session_id: str = None  # Optional chat session ID for multi-chat support

@router.post("/chat")
async def chat(
    payload: ChatRequest,
    chat_agent: MistralMCPChatAgent = Depends(get_chat_agent)
):
    """
    Depends() function in FastAPI is a dependency injection mechanism.
    It allows FastAPI to:
    1. Automatically resolve and inject objects into your endpoint functions.
    2. Handle lifecycles, such as:
    - Singleton (shared across requests)
    - Per-request construction
    3. Support overrides, useful for:
    - Swapping out implementations without touching route logic
    4. Declare clear contracts — your route declares what it needs, and FastAPI wires it in.
    """
    print("Hit the chat endpoint")

    # Validate session and get user
    user = auth_service.validate_session(payload.session_token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please log in again."
        )

    # Check if user has OAuth authentication for Gmail
    creds = load_credentials(user.email)
    if not creds or not creds.valid:
        raise HTTPException(
            status_code=401,
            detail="Gmail not authenticated. Please complete the Google OAuth process."
        )

    # Generate or use provided chat session ID
    chat_session_id = payload.chat_session_id or f"{user.email}_{str(uuid.uuid4())[:8]}"

    print(f"Using chat_session_id: {chat_session_id}")
    print(f"User email: {user.email}")

    try:
        # Use the chat_session_id as the session_id for the LLM to ensure separate
        # conversation histories
        response = await chat_agent.run(payload.input, chat_session_id, user.email)
        return {"response": response, "chat_session_id": chat_session_id}
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )
