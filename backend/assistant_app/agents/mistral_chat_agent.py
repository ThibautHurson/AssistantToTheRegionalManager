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

from backend.assistant_app.agents.base_agent import BaseAgent
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from backend.assistant_app.memory.context_manager import HybridContextManager
from backend.assistant_app.memory.vector_stores.faiss_vector_store import VectorStoreManager
from backend.assistant_app.memory.summarizer import SummarizationManager
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
        self.api_key = os.getenv(self.config.get("api_key_env_var", "MISTRAL_API_KEY"))
        if not self.api_key:
            raise ValueError("Mistral API key not found in environment variables")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = self.config.get("model", "mistral-small-latest")
        
        self.max_steps = max_steps
        self.current_session_id = None

        self.exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self.mcp_tools = []
        self.system_prompt = ""

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

        # Build the dynamic system prompt using MCP prompts
        self.system_prompt = await self.build_dynamic_system_prompt()
        
        # Initialize memory and context components
        history_store = RedisHistoryStore()
        vector_store = VectorStoreManager() # Uses default paths
        summarizer = SummarizationManager()
        self.context_manager = HybridContextManager(
            history_store=history_store,
            vector_store=vector_store,
            summarizer=summarizer,
            system_prompt=self.system_prompt
        )
        print("\nConnected to server with tools:", [tool.name for tool in self.mcp_tools])

    async def build_dynamic_system_prompt(self) -> str:
        """Build a dynamic system prompt using MCP prompts."""
        base_prompt = ""
        
        # Always include the base system prompt using MCP prompt method
        try:
            # Use the proper MCP get_prompt method
            result = await self.session.get_prompt("system_base")
            # Extract text content from the GetPromptResult
            if result.messages and len(result.messages) > 0:
                content = result.messages[0].content
                if hasattr(content, 'text'):
                    base_prompt = content.text
                else:
                    base_prompt = str(content)
            else:
                base_prompt = "You are an intelligent personal assistant that helps users manage their tasks and emails."
        except Exception as e:
            print(f"Could not fetch system_base prompt: {e}")
            base_prompt = "You are an intelligent personal assistant that helps users manage their tasks and emails."
        
        # Add tool descriptions
        tool_descriptions = "\n\n## Available Tools\n"
        for tool in self.mcp_tools:
            tool_descriptions += f"- **{tool.name}**: {tool.description}\n"
        
        return base_prompt + tool_descriptions

    async def get_contextual_prompt(self, user_query: str) -> str:
        """Get contextual prompts based on the user's query."""
        contextual_prompts = []
        
        # Analyze query to determine relevant prompts
        query_lower = user_query.lower()
        
        # Task-related queries
        if any(word in query_lower for word in ['task', 'todo', 'priority', 'due', 'deadline', 'create', 'add', 'list', 'update', 'delete']):
            try:
                result = await self.session.get_prompt("task_management")
                if result.messages and len(result.messages) > 0:
                    content = result.messages[0].content
                    if hasattr(content, 'text'):
                        contextual_prompts.append(content.text)
                    else:
                        contextual_prompts.append(str(content))
            except Exception as e:
                print(f"Could not fetch task_management prompt: {e}")
        
        # Email-related queries
        if any(word in query_lower for word in ['email', 'gmail', 'search', 'send', 'reply', 'inbox', 'message']):
            try:
                result = await self.session.get_prompt("email_assistant")
                if result.messages and len(result.messages) > 0:
                    content = result.messages[0].content
                    if hasattr(content, 'text'):
                        contextual_prompts.append(content.text)
                    else:
                        contextual_prompts.append(str(content))
            except Exception as e:
                print(f"Could not fetch email_assistant prompt: {e}")
        
        # Productivity-related queries
        if any(word in query_lower for word in ['productivity', 'time', 'schedule', 'organize', 'efficient', 'workflow']):
            try:
                result = await self.session.get_prompt("productivity_coach")
                if result.messages and len(result.messages) > 0:
                    content = result.messages[0].content
                    if hasattr(content, 'text'):
                        contextual_prompts.append(content.text)
                    else:
                        contextual_prompts.append(str(content))
            except Exception as e:
                print(f"Could not fetch productivity_coach prompt: {e}")
        
        # Always include conversation context for continuity
        try:
            result = await self.session.get_prompt("conversation_context")
            if result.messages and len(result.messages) > 0:
                content = result.messages[0].content
                if hasattr(content, 'text'):
                    contextual_prompts.append(content.text)
                else:
                    contextual_prompts.append(str(content))
        except Exception as e:
            print(f"Could not fetch conversation_context prompt: {e}")
        
        return "\n\n".join(contextual_prompts)

    async def run(self, query: str, session_id: str) -> str:
        """
        Multi-step chat with dynamic prompt management. Handles tool calls via MCP and returns the final assistant message.
        """
        # Get contextual prompts based on the user's query
        contextual_prompt = await self.get_contextual_prompt(query)
        
        # Get the hybrid context, now including the user query for RAG
        llm_context = await self.context_manager.get_context(session_id, user_query=query)
        
        # Add contextual prompt if available
        if contextual_prompt:
            llm_context.insert(0, {"role": "system", "content": contextual_prompt})
        
        llm_context.append({"role": "user", "content": query})
        new_messages_this_turn = [{"role": "user", "content": query}]

        tool_schemas = []
        for tool in self.mcp_tools:
            # Deep copy to avoid mutating the original schema
            params = copy.deepcopy(tool.inputSchema)
            # Agent filters the schemas to remove session_id before sending to LLM
            if "properties" in params and "session_id" in params["properties"]:
                del params["properties"]["session_id"]
            if "required" in params and "session_id" in params["required"]:
                params["required"] = [r for r in params["required"] if r != "session_id"]
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
                    tool_args["session_id"] = session_id
                    
                    # Enhanced error handling for tool calls
                    try:
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
                await self.context_manager.save_new_messages(session_id, new_messages_this_turn)
                print(llm_context)
                return content

        # Fallback if max_steps is reached
        final_content = llm_context[-1].get("content", "Max steps reached.")
        await self.context_manager.save_new_messages(session_id, new_messages_this_turn)
        return final_content

    async def cleanup(self):
        await self.exit_stack.aclose()