from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json

from backend.assistant_app.agents.mistral_chat_agent import MistralChatAgent
import backend.assistant_app.agents.tools  # this triggers registration
from backend.assistant_app.utils.tool_registry import tool_registry
from backend.assistant_app.agents.prompts.prompt_builder import build_system_prompt
from backend.assistant_app.agents.tools.tools_schema import tools_schema
from backend.assistant_app.api_integration.google_token_store import load_credentials

with open("backend/assistant_app/configs/chat_config.json") as f:
    config = json.load(f)

tools = tool_registry.keys()
print("Tool registry", tools)
system_prompt = build_system_prompt(tools)

# Global instance (singleton pattern)
_chat_agent = MistralChatAgent(
    config=config,
    system_prompt=system_prompt,
    tools=tools_schema,
)

def get_chat_agent() -> MistralChatAgent:
    return _chat_agent

class ChatRequest(BaseModel):
    input: str
    session_id: str

router = APIRouter()

@router.post("/chat")
async def chat(
    payload: ChatRequest,
    chat_agent: MistralChatAgent = Depends(get_chat_agent)
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
        content = await chat_agent.run(input_data=payload.input, 
                                    session_id=payload.session_id)
        return {"response": content}
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )