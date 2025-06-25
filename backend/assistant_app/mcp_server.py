from mcp.server.fastmcp import FastMCP
import os
mcp = FastMCP("assistant-mcp-server")

# --- Gmail Tools ---
from backend.assistant_app.agents.tools.gmail_tools import search_gmail, send_gmail, reply_to_gmail

@mcp.tool()
async def search_gmail_tool(query: str, session_id: str) -> str:
    results = await search_gmail(query, session_id)
    return str(results)

@mcp.tool()
async def send_gmail_tool(to: str, subject: str, body: str, session_id: str) -> str:
    result = await send_gmail(to, subject, body, session_id)
    return str(result)

@mcp.tool()
async def reply_to_gmail_tool(message_id: str, body: str, session_id: str) -> str:
    result = await reply_to_gmail(message_id, body, session_id)
    return str(result)

# --- Agent Task Tools ---
from backend.assistant_app.agents.tools.agent_task_tools import add_task, delete_task, update_task, list_tasks, get_next_task

@mcp.tool()
async def add_task_tool(session_id: str, title: str, description: str = None, due_date: str = None, priority: int = 1) -> str:
    result = add_task(session_id, title, description, due_date, priority)
    return str(result)

@mcp.tool()
async def delete_task_tool(session_id: str, task_id: str) -> str:
    result = delete_task(session_id, task_id)
    return str(result)

@mcp.tool()
async def update_task_tool(session_id: str, task_id: str, title: str = None, description: str = None, due_date: str = None, priority: int = None, status: str = None) -> str:
    kwargs = {k: v for k, v in {"title": title, "description": description, "due_date": due_date, "priority": priority, "status": status}.items() if v is not None}
    result = update_task(session_id, task_id, **kwargs)
    return str(result)

@mcp.tool()
async def list_tasks_tool(session_id: str, status: str = None, priority: int = None) -> str:
    result = list_tasks(session_id, status, priority)
    return str(result)

@mcp.tool()
async def get_next_task_tool(session_id: str) -> str:
    result = get_next_task(session_id)
    return str(result)

if __name__ == "__main__":
    mcp.run(transport='stdio') 