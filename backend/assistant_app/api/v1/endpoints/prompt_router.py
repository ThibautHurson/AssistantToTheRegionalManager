from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.assistant_app.agents.mistral_chat_agent import MistralMCPChatAgent

# FastAPI router
router = APIRouter()

def get_chat_agent() -> MistralMCPChatAgent:
    # Import here to avoid circular imports
    from backend.assistant_app.api.v1.endpoints.chat import agent
    return agent

def extract_mcp_content(result) -> str:
    """Extract text content from MCP tool result."""
    if isinstance(result.content, list):
        # If it's a list of TextContent objects, extract the text from each
        content_parts = []
        for item in result.content:
            if hasattr(item, 'text'):
                content_parts.append(item.text)
            else:
                content_parts.append(str(item))
        return '\n'.join(content_parts)
    elif hasattr(result.content, 'text'):
        return result.content.text
    else:
        return str(result.content)

class PromptUpdateRequest(BaseModel):
    prompt_name: str
    content: str

class PromptCreateRequest(BaseModel):
    prompt_name: str
    content: str

@router.get("/prompts")
async def list_prompts(
    chat_agent: MistralMCPChatAgent = Depends(get_chat_agent)
):
    """List all available prompt templates."""
    try:
        # Directly call the MCP tool
        result = await chat_agent.session.call_tool("list_available_prompts", {})
        return {"prompts": extract_mcp_content(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing prompts: {str(e)}")

@router.get("/prompts/{prompt_name}")
async def get_prompt(
    prompt_name: str,
    chat_agent: MistralMCPChatAgent = Depends(get_chat_agent)
):
    """Get a specific prompt template."""
    try:
        # Directly call the MCP tool
        result = await chat_agent.session.call_tool("get_prompt_template", {
            "prompt_name": prompt_name
        })
        return {"prompt": extract_mcp_content(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting prompt: {str(e)}")

@router.put("/prompts/{prompt_name}")
async def update_prompt(
    prompt_name: str,
    request: PromptUpdateRequest,
    chat_agent: MistralMCPChatAgent = Depends(get_chat_agent)
):
    """Update a prompt template."""
    try:
        # Directly call the MCP tool
        result = await chat_agent.session.call_tool("update_prompt_template", {
            "prompt_name": prompt_name,
            "new_content": request.content
        })
        return {"message": extract_mcp_content(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating prompt: {str(e)}")

@router.post("/prompts")
async def create_prompt(
    request: PromptCreateRequest,
    chat_agent: MistralMCPChatAgent = Depends(get_chat_agent)
):
    """Create a new prompt template."""
    try:
        # Directly call the MCP tool
        result = await chat_agent.session.call_tool("create_prompt_template", {
            "prompt_name": request.prompt_name,
            "content": request.content
        })
        return {"message": extract_mcp_content(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating prompt: {str(e)}")
    