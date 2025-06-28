from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
import os

from backend.assistant_app.agents.mistral_chat_agent import MistralMCPChatAgent
from backend.assistant_app.api_integration.google_token_store import load_credentials

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
    session_id: str

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
    
    # Check if user is authenticated
    creds = load_credentials(payload.session_id)
    if not creds or not creds.valid:
        raise HTTPException(
            status_code=401,
            detail="User not authenticated. Please complete the Google authentication process."
        )
    
    try:
        response = await chat_agent.run(payload.input, payload.session_id)
        return {"response": response}
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )