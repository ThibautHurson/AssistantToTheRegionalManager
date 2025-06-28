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

def load_prompt_from_file(prompt_name: str) -> str:
    """Load prompt content from external file."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_dir = os.path.join(script_dir, "agents", "prompts")
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
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_dir = os.path.join(script_dir, "agents", "prompts")
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
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_dir = os.path.join(script_dir, "agents", "prompts")
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
async def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web for relevant information and return URLs that can be fetched.
    This tool finds relevant web pages that can then be fetched using the fetch tool.
    
    Args:
        query: The search query (e.g., "latest AI news", "Python 3.12 features")
        num_results: Number of search results to return (default 5, max 10)
    
    Returns:
        str: JSON-formatted list of search results with titles, URLs, and snippets
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
        
        # Check if this is a news query
        news_keywords = ['news', 'latest', 'breaking', 'update', 'today', 'recent', 'current']
        is_news_query = any(keyword in query.lower() for keyword in news_keywords)
        
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
                # Try a different approach - look for any links with titles
                links = soup.find_all('a', href=True)
                for link in links[:num_results]:
                    url = link.get('href', '')
                    title = link.get_text(strip=True)
                    
                    if url.startswith('http') and title and len(title) > 10:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": f"Found via web search for: {query}",
                            "source": "DuckDuckGo"
                        })
            
            if not results:
                return json.dumps({
                    "error": f"No search results found for: {query}",
                    "suggestions": [
                        "Try a different search term",
                        "Check spelling", 
                        "Use more specific keywords",
                        "The search engine might be temporarily unavailable"
                    ]
                })
            
            # Add guidance based on query type
            response_data = {
                "query": query,
                "results": results,
                "count": len(results),
                "note": "Use the fetch tool with any of these URLs to get the full content"
            }
            
            if is_news_query:
                response_data["news_note"] = "IMPORTANT: To provide you with actual news content, please use the fetch tool with these URLs to get the latest articles and information. Don't just list the URLs - fetch the content and provide a comprehensive summary of the latest developments."
                response_data["fetch_instruction"] = "Use the fetch tool to get the actual news content from these sources and provide a comprehensive summary of the latest developments."
                response_data["summary_guidance"] = "After fetching content, create a synthesized summary that combines information from all sources, highlighting the most important developments. CRITICAL: End with a 'Sources:' section using proper markdown links like [Source Name](URL). NEVER use [REF] format."
                response_data["source_reminder"] = "🚨 CRITICAL: When providing sources, ALWAYS use [Source Name](URL) format and NEVER use [REF] format. End your response with a 'Sources:' section."
            
            return json.dumps(response_data)
            
    except Exception as e:
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "query": query
        })

@mcp.tool()
async def smart_web_research(query: str, max_results: int = 3) -> str:
    """
    Perform intelligent web research by searching and providing guidance on what to fetch.
    This tool helps determine the best approach for finding information online.
    
    Args:
        query: The research topic or question
        max_results: Maximum number of sources to suggest
    
    Returns:
        str: Research guidance and suggested URLs to fetch
    """
    try:
        # Check if this is a news query
        news_keywords = ['news', 'latest', 'breaking', 'update', 'today', 'recent', 'current']
        is_news_query = any(keyword in query.lower() for keyword in news_keywords)
        
        # First, perform a web search
        search_results = await web_search(query, max_results)
        search_data = json.loads(search_results)
        
        if "error" in search_data:
            return search_results
        
        # Provide intelligent guidance
        guidance = f"Research Query: {query}\n\n"
        
        if is_news_query:
            guidance += "📰 **News Research**\n\n"
            guidance += "**CRITICAL:** To provide actual news content, you MUST use the fetch tool!\n"
            guidance += "Don't just list URLs - fetch the content and provide real information.\n\n"
            guidance += "**SUMMARY APPROACH:**\n"
            guidance += "- Fetch content from multiple sources\n"
            guidance += "- Create a synthesized summary combining all sources\n"
            guidance += "- Highlight the most important developments\n"
            guidance += "- Include source links as references\n"
            guidance += "- Avoid detailed bullet points - focus on key insights\n\n"
        else:
            guidance += "Suggested approach:\n"
        
        guidance += "1. Use the 'fetch' tool with the URLs below to get detailed content\n"
        guidance += "2. Focus on the most relevant sources first\n"
        guidance += "3. Cross-reference information from multiple sources\n\n"
        
        guidance += "Recommended sources to fetch:\n"
        for i, result in enumerate(search_data["results"], 1):
            guidance += f"{i}. {result['title']}\n"
            guidance += f"   URL: {result['url']}\n"
            guidance += f"   Preview: {result['snippet'][:100]}...\n\n"
        
        guidance += "Next steps:\n"
        guidance += "- Use the 'fetch' tool with any of the URLs above\n"
        guidance += "- Ask follow-up questions based on the fetched content\n"
        guidance += "- Request summaries or specific information from the sources\n"
        
        if is_news_query:
            guidance += "\n**News-Specific Instructions:**\n"
            guidance += "- FETCH the actual articles using the fetch tool\n"
            guidance += "- Create a synthesized summary combining all sources\n"
            guidance += "- Organize by themes/developments, not by source\n"
            guidance += "- Highlight the most important developments\n"
            guidance += "- CRITICAL: End with a 'Sources:' section using proper markdown links\n"
            guidance += "- ALWAYS use [Source Name](URL) format - NEVER use [REF] format\n"
            guidance += "- Include clickable links to all URLs used\n"
            guidance += "- Avoid detailed bullet points - focus on key insights\n"
            guidance += "- Provide a cohesive narrative, not source-by-source breakdown\n"
            guidance += "\n🚨 **SOURCE ATTRIBUTION REMINDER:**\n"
            guidance += "🚨 ALWAYS use [Source Name](URL) format - NEVER use [REF] format\n"
            guidance += "🚨 End your response with a 'Sources:' section\n"
            guidance += "🚨 Make all source links clickable\n"
        
        return guidance
        
    except Exception as e:
        return f"Research failed: {str(e)}"

@mcp.tool()
async def generate_citations(search_results_json: str, format_type: str = "markdown") -> str:
    """
    Generate properly formatted citations from web search results.
    
    Args:
        search_results_json: JSON string containing search results from web_search tool
        format_type: Citation format - "markdown", "text", or "html"
    
    Returns:
        str: Formatted citations and source information
    """
    try:
        import json
        from datetime import datetime
        
        results = json.loads(search_results_json)
        
        if "error" in results:
            return f"Error: {results['error']}"
        
        if "results" not in results:
            return "No results to cite"
        
        citations = []
        sources_summary = []
        
        for i, result in enumerate(results["results"], 1):
            title = result.get("title", "Unknown Title")
            url = result.get("url", "")
            domain = result.get("domain", "")
            snippet = result.get("snippet", "")
            
            if format_type == "markdown":
                citation = f"{i}. [{title}]({url})"
                source_info = f"   - **Domain**: {domain}"
                if snippet:
                    source_info += f"\n   - **Summary**: {snippet[:150]}..."
                citations.append(citation)
                sources_summary.append(source_info)
                
            elif format_type == "text":
                citation = f"{i}. {title} - {url}"
                source_info = f"   Domain: {domain}"
                if snippet:
                    source_info += f"\n   Summary: {snippet[:150]}..."
                citations.append(citation)
                sources_summary.append(source_info)
                
            elif format_type == "html":
                citation = f'<li><a href="{url}">{title}</a></li>'
                source_info = f'<p><strong>Domain:</strong> {domain}</p>'
                if snippet:
                    source_info += f'<p><strong>Summary:</strong> {snippet[:150]}...</p>'
                citations.append(citation)
                sources_summary.append(source_info)
        
        # Combine citations and sources
        if format_type == "markdown":
            output = "## Sources\n\n"
            for citation, source_info in zip(citations, sources_summary):
                output += f"{citation}\n{source_info}\n\n"
            output += f"\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            
        elif format_type == "text":
            output = "SOURCES:\n\n"
            for citation, source_info in zip(citations, sources_summary):
                output += f"{citation}\n{source_info}\n\n"
            output += f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        elif format_type == "html":
            output = "<h2>Sources</h2><ul>"
            for citation in citations:
                output += citation
            output += "</ul>"
            for source_info in sources_summary:
                output += source_info
            output += f"<p><em>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>"
        
        return output
        
    except Exception as e:
        return f"Error generating citations: {str(e)}"

@mcp.tool()
async def search_with_sources(query: str, num_results: int = 5, include_citations: bool = True) -> str:
    """
    Search the web and return results with proper source attribution and citations.
    
    Args:
        query: The search query
        num_results: Number of search results to return (default 5, max 10)
        include_citations: Whether to include formatted citations in the response
    
    Returns:
        str: Search results with source information and optional citations
    """
    try:
        # Check if this is a news query
        news_keywords = ['news', 'latest', 'breaking', 'update', 'today', 'recent', 'current']
        is_news_query = any(keyword in query.lower() for keyword in news_keywords)
        
        # Perform the web search
        search_results = await web_search(query, num_results)
        search_data = json.loads(search_results)
        
        if "error" in search_data:
            return search_results
        
        # Add source summary
        output = f"## Search Results for: {query}\n\n"
        output += f"Found {search_data['count']} relevant sources:\n\n"
        
        for i, result in enumerate(search_data["results"], 1):
            output += f"### {i}. {result['title']}\n"
            output += f"**URL**: {result['url']}\n"
            output += f"**Domain**: {result['domain']}\n"
            output += f"**Summary**: {result['snippet'][:200]}...\n\n"
        
        # Add special instructions for news queries
        if is_news_query:
            output += "## 📰 **IMPORTANT: News Content Instructions**\n\n"
            output += "**To provide you with actual news information, I need to fetch the content from these sources.**\n\n"
            output += "**Next Steps:**\n"
            output += "1. I will use the 'fetch' tool to get the actual articles\n"
            output += "2. I will create a synthesized summary combining all sources\n"
            output += "3. I will highlight the most important developments\n"
            output += "4. CRITICAL: I will end with a 'Sources:' section using proper markdown links\n"
            output += "5. ALWAYS use [Source Name](URL) format - NEVER use [REF] format\n"
            output += "6. I will avoid detailed bullet points - focus on key insights\n\n"
            output += "**Source Attribution Format:**\n"
            output += "- End your response with a 'Sources:' section\n"
            output += "- List each source as: [Source Name](URL)\n"
            output += "- Example: [Al Jazeera](https://www.aljazeera.com/where/iran/)\n"
            output += "- NEVER use [REF] format - ALWAYS use proper markdown links\n\n"
            output += "🚨 **CRITICAL REMINDER:**\n"
            output += "🚨 ALWAYS use [Source Name](URL) format - NEVER use [REF] format\n"
            output += "🚨 End your response with a 'Sources:' section\n"
            output += "🚨 Make all source links clickable\n\n"
            output += "**Please wait while I fetch and analyze the actual news content...**\n\n"
        
        # Add citations if requested
        if include_citations:
            citations = await generate_citations(search_results, "markdown")
            output += citations
        
        return output
        
    except Exception as e:
        return f"Error in search with sources: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')