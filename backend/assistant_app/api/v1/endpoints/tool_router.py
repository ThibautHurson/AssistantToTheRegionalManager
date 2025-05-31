from fastapi import APIRouter, HTTPException
from app.services.tools.runner import run_tool

router = APIRouter()

@router.post("/tools/run")
async def run_tool_endpoint(tool_name: str, args: dict):
    try:
        return run_tool(tool_name, **args)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))