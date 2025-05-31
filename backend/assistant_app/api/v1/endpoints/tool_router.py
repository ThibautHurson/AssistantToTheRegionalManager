from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import backend.assistant_app.agents.tools
from backend.assistant_app.utils.tool_registry import tool_registry

class ToolCallRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any]

router = APIRouter()

@router.post("/tools/run")
async def run_tool_endpoint(request: ToolCallRequest):
    try:
        print(tool_registry)
        return tool_registry.get(request.tool_name)(**request.args)
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Exception while calling tool '{request.tool_name}': {traceback_str}")
        raise HTTPException(status_code=400, detail=str(e))