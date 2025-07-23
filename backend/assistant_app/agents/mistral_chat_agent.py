from mistralai import Mistral
import os
from dotenv import load_dotenv
import json
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mistralai.models import sdkerror
import copy
import re

from backend.assistant_app.agents.base_agent import BaseAgent
from backend.assistant_app.memory.context_manager import HybridContextManager
from backend.assistant_app.utils.handle_errors import retry_on_rate_limit_async

class MistralMCPChatAgent(BaseAgent):
    """
    An agent that orchestrates Mistral LLM chat and MCP tool use.
    Connects to an MCP server, dynamically discovers tools, and routes LLM tool calls to MCP.
    Supports multi-step tool use (max_steps) and dynamic prompt management.
    """
    def __init__(self, config=None, max_steps=5):
        load_dotenv()
        self.config = config or {}
        self.api_key = os.getenv("MISTRAL_KEY")
        if not self.api_key:
            raise ValueError("Mistral API key not found in environment variables")

        self.client = Mistral(api_key=self.api_key)
        self.model = self.config.get("model", "mistral-small-latest")
        self.max_steps = max_steps
        self.current_session_id = None
        self.exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self.mcp_tools = []

    @retry_on_rate_limit_async(
        max_attempts=5,
        wait_seconds=1,
        retry_on=sdkerror.SDKError
    )
    async def call_mistral_with_retry(self, messages, tools):
        print("Calling mistral")
        response = await self.client.chat.complete_async(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        return response

    async def connect_to_server(self, server_script_path: str):
        """Connect to the MCP server and cache available tools and prompts."""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=os.environ.copy()
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # List and cache available tools
        response = await self.session.list_tools()
        self.mcp_tools = response.tools

        print("\nConnected to server with tools:", [tool.name for tool in self.mcp_tools])

    async def connect_to_fetch_server(self):
        """Connect to the official MCP Fetch server for web content fetching."""
        try:
            # Connect to the official fetch server
            fetch_server_params = StdioServerParameters(
                command="python",
                args=["-m", "mcp_server_fetch"],
                env=os.environ.copy()
            )
            fetch_transport = await self.exit_stack.enter_async_context(stdio_client(fetch_server_params))
            fetch_stdio, fetch_write = fetch_transport
            self.fetch_session = await self.exit_stack.enter_async_context(ClientSession(fetch_stdio, fetch_write))
            await self.fetch_session.initialize()

            # Get fetch server tools
            fetch_response = await self.fetch_session.list_tools()
            fetch_tools = fetch_response.tools

            # Add fetch tools to the main tools list
            self.mcp_tools.extend(fetch_tools)

            print(f"Connected to fetch server with tools: {[tool.name for tool in fetch_tools]}")

        except Exception as e:
            print(f"Warning: Could not connect to fetch server: {e}")
            print("Web fetching capabilities will not be available")
            self.fetch_session = None

    def _cleanup_source_references(self, content: str) -> str:
        """Clean up any remaining [REF] format references and ensure proper source attribution."""
        # Remove any [REF]tool_id[/REF] references
        content = re.sub(r'\[REF\][^\[\]]*\[/REF\]', '', content)

        # If content contains URLs but no proper Sources section, add one
        url_pattern = r'https?://[^\s\)]+'
        urls = re.findall(url_pattern, content)

        if urls and 'Sources:' not in content and '**Sources:**' not in content:
            # Extract domain names for source names
            sources = []
            for url in urls:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    source_name = domain.replace('www.', '').replace('.com', '').replace('.org', '').replace('.net', '')
                    source_name = source_name.title()
                    sources.append(f"- [{source_name}]({url})")
                except:
                    sources.append(f"- [Source]({url})")

            if sources:
                content += "\n\n**Sources:**\n" + "\n".join(sources)

        return content

    async def run(self, query: str, session_id: str, user_email: str = None) -> str:
        """
        Multi-step chat with unified context management. Handles tool calls via MCP and returns the final assistant message.

        Args:
            query: The user's input query
            session_id: Unique session identifier for context management
            user_email: User's email address for tool calls (optional, defaults to session_id for backward compatibility)
        """
        # Use session_id as user_email if not provided (backward compatibility)
        if user_email is None:
            user_email = session_id

        # Get user-specific context manager
        context_manager = HybridContextManager(
            mcp_session=self.session,
            user_id=user_email
        )

        # Get the complete context including dynamic system prompt
        llm_context = await context_manager.get_context(session_id, user_query=query)

        # Add the current user query
        llm_context.append({"role": "user", "content": query})
        new_messages_this_turn = [{"role": "user", "content": query}]

        tool_schemas = []
        for tool in self.mcp_tools:
            # Deep copy to avoid mutating the original schema
            params = copy.deepcopy(tool.inputSchema)
            # Agent filters the schemas to remove user_email before sending to LLM
            if "properties" in params and "user_email" in params["properties"]:
                del params["properties"]["user_email"]
            if "required" in params and "user_email" in params["required"]:
                params["required"] = [r for r in params["required"] if r != "user_email"]
            tool_schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": params
                }
            })

        for step in range(self.max_steps):
            print(f"Step {step+1}")
            response = await self.call_mistral_with_retry(
                messages=llm_context,
                tools=tool_schemas,
            )
            message = response.choices[0].message

            # Append new message to both the temporary LLM context and our list of new messages
            llm_context.append(message.model_dump())
            new_messages_this_turn.append(message.model_dump())

            # Step 1: Check if the LLM wants to call a tool
            if message.tool_calls:
                tool_outputs = []
                for tool_call in message.tool_calls:
                    print(f"Tool chosen by Mistral: {tool_call.function.name}")
                    print(f"Tool arguments: {tool_call.function.arguments}")
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Add user_email for tools that need it
                    if tool_name not in ['smart_web_search', 'search_with_sources']:  # Web search tools don't need user_email
                        tool_args["user_email"] = user_email

                    # Enhanced error handling for tool calls
                    try:
                        # Route fetch tools to fetch server, others to main server
                        if tool_name in ['fetch'] and self.fetch_session:
                            result = await self.fetch_session.call_tool(tool_name, tool_args)
                        else:
                            result = await self.session.call_tool(tool_name, tool_args)

                        # Convert the result to a string
                        content = result.content
                        if isinstance(content, list):
                            # Join all .text fields if they exist
                            content_str = "\n".join(
                                getattr(item, "text", str(item)) for item in content
                            )
                        elif hasattr(content, "text"):
                            content_str = content.text
                        else:
                            content_str = str(content)

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": content_str
                        })
                    except Exception as e:
                        # Get error handling prompt for better error responses
                        try:
                            result = await self.session.get_prompt("error_handling")
                            if result.messages and len(result.messages) > 0:
                                content = result.messages[0].content
                                if hasattr(content, 'text'):
                                    error_context = content.text
                                else:
                                    error_context = str(content)
                            else:
                                error_context = "Provide helpful error recovery suggestions."
                        except:
                            error_context = "Provide helpful error recovery suggestions."

                        # Graceful error handling with contextual prompt
                        error_content = f"Tool '{tool_name}' failed: {str(e)}. {error_context}"
                        print(f"Tool error: {error_content}")
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": error_content
                        })

                # Append tool results to both contexts
                llm_context.extend(tool_outputs)
                new_messages_this_turn.extend(tool_outputs)
                continue  # Go to next LLM step with tool outputs

            # Step 2: LLM gives a final answer (no tools)
            else:
                content = message.content
                await context_manager.save_new_messages(session_id, new_messages_this_turn)
                print(llm_context)
                return self._cleanup_source_references(content)

        # Fallback if max_steps is reached
        final_content = llm_context[-1].get("content", "Max steps reached.")
        await context_manager.save_new_messages(session_id, new_messages_this_turn)
        return self._cleanup_source_references(final_content)

    async def cleanup(self):
        await self.exit_stack.aclose()

    def clear_user_data(self, user_email: str):
        """Clear all data for a specific user (for privacy compliance)."""
        from backend.assistant_app.services.user_data_service import UserDataService

        # Use the dedicated user data service for comprehensive deletion
        user_data_service = UserDataService()
        results = user_data_service.clear_user_data(user_email)

        if results["success"]:
            print(f"Successfully cleared all data for user: {user_email}")
        else:
            print(f"Completed data deletion for user: {user_email} with errors: {results['errors']}")

        return results