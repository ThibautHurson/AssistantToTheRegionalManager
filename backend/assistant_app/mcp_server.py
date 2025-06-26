from mcp.server.fastmcp import FastMCP
import os
mcp = FastMCP("assistant-mcp-server")

# --- Gmail Tools ---
from backend.assistant_app.agents.tools.gmail_tools import search_gmail, send_gmail, reply_to_gmail

@mcp.tool()
async def search_gmail_tool(query: str, session_id: str) -> str:
    """
    Search Gmail messages for a given query string.
    Args:
        query: The Gmail search query (e.g., 'from:alice@example.com').
    Returns:
        str: JSON-formatted list of matching messages with content and Gmail links.
    """
    results = await search_gmail(query, session_id)
    return str(results)

@mcp.tool()
async def send_gmail_tool(to: str, subject: str, body: str, session_id: str) -> str:
    """
    Send an email using Gmail.
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
    Returns:
        str: Confirmation message with a link to the sent email.
    """
    result = await send_gmail(to, subject, body, session_id)
    return str(result)

@mcp.tool()
async def reply_to_gmail_tool(message_id: str, body: str, session_id: str) -> str:
    """
    Reply to an existing email using Gmail.
    Args:
        message_id: The ID of the message to reply to
        body: The reply body (plain text)
    Returns:
        str: Confirmation message with a link to the sent reply.
    """
    result = await reply_to_gmail(message_id, body, session_id)
    return str(result)

# --- Agent Task Tools ---
from backend.assistant_app.agents.tools.agent_task_tools import add_task, delete_task, update_task, list_tasks, get_next_task

@mcp.tool()
async def add_task_tool(session_id: str, title: str, description: str = None, due_date: str = None, priority: int = 1) -> str:
    """
    Add a new task to the task manager.
    Args:
        title: The title of the task
        description: Optional description of the task
        due_date: Optional due date for the task (ISO format string)
        priority: Task priority (1-5, default 1)
    Returns:
        str: A message indicating the task was added successfully
    """
    result = add_task(session_id, title, description, due_date, priority)
    return str(result)

@mcp.tool()
async def delete_task_tool(session_id: str, task_id: str) -> str:
    """
    Delete a task from the task manager.
    Args:
        task_id: The ID of the task to delete
    Returns:
        str: A message indicating the task was deleted successfully or not found
    """
    result = delete_task(session_id, task_id)
    return str(result)

@mcp.tool()
async def update_task_tool(session_id: str, task_id: str, title: str = None, description: str = None, due_date: str = None, priority: int = None, status: str = None) -> str:
    """
    Update a task in the task manager.
    Args:
        task_id: The ID of the task to update
        title: New title (optional)
        description: New description (optional)
        due_date: New due date (optional, ISO format string)
        priority: New priority (optional)
        status: New status (optional)
    Returns:
        str: A message indicating the task was updated successfully or not found
    """
    kwargs = {k: v for k, v in {"title": title, "description": description, "due_date": due_date, "priority": priority, "status": status}.items() if v is not None}
    result = update_task(session_id, task_id, **kwargs)
    return str(result)

@mcp.tool()
async def list_tasks_tool(session_id: str, status: str = None, priority: int = None) -> str:
    """
    List all tasks for the user, optionally filtered by status or priority.
    Args:
        status: Optional status filter (e.g., 'pending', 'completed')
        priority: Optional priority filter (1-5)
    Returns:
        str: A formatted list of tasks
    """
    result = list_tasks(session_id, status, priority)
    return str(result)

@mcp.tool()
async def get_next_task_tool(session_id: str) -> str:
    """
    Get the next task based on priority and due date.
    Returns:
        str: Information about the next task or a message if none are pending
    """
    result = get_next_task(session_id)
    return str(result)

if __name__ == "__main__":
    mcp.run(transport='stdio') 