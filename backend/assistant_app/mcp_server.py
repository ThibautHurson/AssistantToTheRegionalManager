from mcp.server.fastmcp import FastMCP
import mcp.types as types
import os
import json
import httpx
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

mcp = FastMCP(
    "assistant-mcp-server",
    description="Personal assistant server with Gmail and task management capabilities"
)

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

# --- MCP Prompts ---
# Centralized prompt management using external files

def get_prompt_dir_path() -> str:
    """Get the full path to the prompt directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "agents", "prompts")

def load_prompt_from_file(prompt_name: str) -> str:
    """Load prompt content from external file."""
    prompt_dir = get_prompt_dir_path()
    prompt_file = os.path.join(prompt_dir, f"{prompt_name}.md")
    
    if os.path.exists(prompt_file):
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    else:
        # Fallback to default prompts if file doesn't exist
        return get_default_prompt(prompt_name)

def get_default_prompt(prompt_name: str) -> str:
    """Fallback default prompts if files don't exist."""
    defaults = {
        "system_base": "You are an intelligent personal assistant that helps users manage their tasks and emails.",
        "task_management": "You are a task management expert. Help users organize their work effectively.",
        "email_assistant": "You are an email communication expert. Help users manage their inbox effectively.",
        "conversation_context": "Maintain conversation context and provide continuity in your responses.",
        "error_handling": "When tools fail or errors occur, help users recover gracefully.",
        "productivity_coach": "You are a productivity coach helping users optimize their workflow."
    }
    return defaults.get(prompt_name, "Prompt template not found.")

@mcp.prompt("system_base")
async def get_system_base_prompt() -> types.GetPromptResult:
    """
    Base system prompt that defines the assistant's core personality and capabilities.
    """
    content = load_prompt_from_file("system_base")
    return types.GetPromptResult(
        messages=[types.PromptMessage(role="assistant", content=types.TextContent(type="text", text=content))]
    )

@mcp.prompt("task_management")
async def get_task_management_prompt() -> types.GetPromptResult:
    """
    Specialized prompt for task management operations.
    """
    content = load_prompt_from_file("task_management")
    return types.GetPromptResult(
        messages=[types.PromptMessage(role="assistant", content=types.TextContent(type="text", text=content))]
    )

@mcp.prompt("email_assistant")
async def get_email_assistant_prompt() -> types.GetPromptResult:
    """
    Specialized prompt for email operations.
    """
    content = load_prompt_from_file("email_assistant")
    return types.GetPromptResult(
        messages=[types.PromptMessage(role="assistant", content=types.TextContent(type="text", text=content))]
    )

@mcp.prompt("conversation_context")
async def get_conversation_context_prompt() -> types.GetPromptResult:
    """
    Prompt for maintaining conversation context and continuity.
    """
    content = load_prompt_from_file("conversation_context")
    return types.GetPromptResult(
        messages=[types.PromptMessage(role="assistant", content=types.TextContent(type="text", text=content))]
    )

@mcp.prompt("error_handling")
async def get_error_handling_prompt() -> types.GetPromptResult:
    """
    Prompt for handling errors and providing helpful recovery suggestions.
    """
    content = load_prompt_from_file("error_handling")
    return types.GetPromptResult(
        messages=[types.PromptMessage(role="assistant", content=types.TextContent(type="text", text=content))]
    )

@mcp.prompt("productivity_coach")
async def get_productivity_coach_prompt() -> types.GetPromptResult:
    """
    Prompt for productivity coaching and time management advice.
    """
    content = load_prompt_from_file("productivity_coach")
    return types.GetPromptResult(
        messages=[types.PromptMessage(role="assistant", content=types.TextContent(type="text", text=content))]
    )

@mcp.prompt("web_search_system")
async def get_web_search_system_prompt() -> types.GetPromptResult:
    """Get the web search system prompt for web research queries."""
    content = load_prompt_from_file("web_search_system")
    return types.GetPromptResult(
        messages=[
            types.PromptMessage(
                role="assistant",
                content=types.TextContent(
                    type="text",
                    text=content
                )
            )
        ]
    )

# --- Prompt Management Tools ---
# Tools to help manage and customize prompts

@mcp.tool()
async def get_prompt_template(prompt_name: str) -> str:
    """
    Retrieve a specific prompt template by name.
    Args:
        prompt_name: Name of the prompt template to retrieve
    Returns:
        str: The prompt template content
    """
    return load_prompt_from_file(prompt_name)

@mcp.tool()
async def list_available_prompts() -> str:
    """
    List all available prompt templates.
    Returns:
        str: List of available prompt templates
    """
    prompt_dir = get_prompt_dir_path()
    available_prompts = []
    
    if os.path.exists(prompt_dir):
        files = os.listdir(prompt_dir)
        
        for file in files:
            if file.endswith('.md'):
                prompt_name = file[:-3]  # Remove .md extension
                available_prompts.append(prompt_name)
    
    if not available_prompts:
        # Fallback to hardcoded list if no files found
        available_prompts = [
            "system_base",
            "task_management", 
            "email_assistant",
            "conversation_context",
            "error_handling",
            "productivity_coach"
        ]
    
    result = "Available prompt templates:\n" + "\n".join(f"- {prompt}" for prompt in available_prompts)
    return result

@mcp.tool()
async def update_prompt_template(prompt_name: str, new_content: str) -> str:
    """
    Update a prompt template with new content.
    Args:
        prompt_name: Name of the prompt template to update
        new_content: New content for the prompt
    Returns:
        str: Confirmation message
    """
    prompt_dir = get_prompt_dir_path()
    os.makedirs(prompt_dir, exist_ok=True)
    
    prompt_file = os.path.join(prompt_dir, f"{prompt_name}.md")
    
    try:
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f"Prompt template '{prompt_name}' updated successfully."
    except Exception as e:
        return f"Error updating prompt template: {str(e)}"

@mcp.tool()
async def create_prompt_template(prompt_name: str, content: str) -> str:
    """
    Create a new prompt template.
    Args:
        prompt_name: Name for the new prompt template
        content: Content of the prompt
    Returns:
        str: Confirmation message
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_dir = os.path.join(script_dir, "agents", "prompts")
    os.makedirs(prompt_dir, exist_ok=True)
    
    prompt_file = os.path.join(prompt_dir, f"{prompt_name}.md")
    
    if os.path.exists(prompt_file):
        return f"Prompt template '{prompt_name}' already exists. Use update_prompt_template to modify it."
    
    try:
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Prompt template '{prompt_name}' created successfully."
    except Exception as e:
        return f"Error creating prompt template: {str(e)}"

# --- Web Search Tools ---
@mcp.tool()
async def search_with_sources(query: str, num_results: int = 3, include_citations: bool = True) -> str:
    """
    Search the web and return results with proper source attribution and citations.
    This is the primary web search tool that provides comprehensive results with guidance.
    
    IMPORTANT: Always use num_results=3-5 for comprehensive coverage. Don't rely on just one source.
    
    Args:
        query: The search query (e.g., "latest AI news", "Python 3.12 features")
        num_results: Number of search results to return (default 3, recommended 3-5, max 10)
        include_citations: Whether to include formatted citations in the response
    
    Returns:
        str: Search results with source information, guidance, and optional citations
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
        from datetime import datetime

        # Limit results to reasonable number
        num_results = min(num_results, 10)
        
        # Use DuckDuckGo for search
        search_url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(search_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Try different selectors for DuckDuckGo results
            selectors = [
                'div.result',  # Old selector
                'div.web-result',  # New selector
                'div[data-testid="result"]',  # Another possible selector
                'div.result__body',  # Alternative selector
            ]
            
            for selector in selectors:
                result_elements = soup.select(selector)
                if result_elements:
                    print(f"Found {len(result_elements)} results with selector: {selector}")
                    break
            
            if not result_elements:
                # Fallback: look for any div with links
                result_elements = soup.find_all('div', class_=lambda x: x and 'result' in x.lower())
            
            for result in result_elements[:num_results]:
                # Title and DuckDuckGo redirect URL
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    ddg_url = title_elem.get('href', '')
                    # Extract real URL from uddg param
                    import urllib.parse
                    real_url = None
                    if 'uddg=' in ddg_url:
                        real_url = urllib.parse.unquote(ddg_url.split('uddg=')[1].split('&')[0])
                    elif ddg_url.startswith('http'):
                        real_url = ddg_url
                    else:
                        real_url = None
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    if real_url:
                        results.append({
                            "title": title,
                            "url": real_url,
                            "snippet": snippet,
                            "source": "DuckDuckGo",
                            "domain": urllib.parse.urlparse(real_url).netloc,
                            "citation": f"[{title}]({real_url})"
                        })
            
            if not results:
                # Load error message from prompt file
                error_template = load_prompt_from_file("search_error")
                return json.dumps({
                    "error": f"{error_template}: {query}",
                    "suggestions": [
                        "Try a different search term",
                        "Check spelling", 
                        "Use more specific keywords",
                        "The search engine might be temporarily unavailable"
                    ]
                })
            
            # Build search results content
            search_results_content = ""
            for i, result in enumerate(results, 1):
                search_results_content += f"### {i}. {result['title']}\n"
                search_results_content += f"**URL**: {result['url']}\n"
                search_results_content += f"**Domain**: {result['domain']}\n"
                search_results_content += f"**Summary**: {result['snippet'][:200]}...\n\n"
            
            # Build citations content if requested
            citations_content = ""
            if include_citations:
                citations_content += "## Sources\n\n"
                for i, result in enumerate(results, 1):
                    citations_content += f"{i}. [{result['title']}]({result['url']})\n"
                    citations_content += f"   - **Domain**: {result['domain']}\n"
                    if result['snippet']:
                        citations_content += f"   - **Summary**: {result['snippet'][:150]}...\n"
                    citations_content += "\n"
                citations_content += f"\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            
            # Load and format the comprehensive template
            template = load_prompt_from_file("web_search_template")
            output = template.format(
                query=query,
                count=len(results),
                search_results=search_results_content,
                citations=citations_content
            )
            
            return output
            
    except Exception as e:
        return f"Error in search with sources: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')