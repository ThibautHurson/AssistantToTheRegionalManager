from mistralai import Mistral
import os
from dotenv import load_dotenv
import json
import httpx

from backend.assistant_app.agents.base_agent import BaseAgent
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from backend.assistant_app.memory.context_manager import HybridContextManager
from backend.assistant_app.memory.vector_stores.faiss_vector_store import VectorStoreManager
from backend.assistant_app.memory.summarizer import SummarizationManager
from backend.assistant_app.utils.handle_errors import retry_on_rate_limit_async
from mistralai.models import sdkerror

class MistralChatAgent(BaseAgent):
    def __init__(self, config=None, system_prompt=None, tools=None, max_steps=5):
        load_dotenv()
        super().__init__(config)
        self.config = config or {}
        self.api_key = os.getenv(self.config.get("api_key_env_var", "MISTRAL_API_KEY"))
        if not self.api_key:
            raise ValueError("Mistral API key not found in environment variables")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = self.config.get("model", "mistral-small-latest")
        
        # Initialize memory and context components
        history_store = RedisHistoryStore()
        vector_store = VectorStoreManager() # Uses default paths
        summarizer = SummarizationManager()
        self.context_manager = HybridContextManager(
            history_store=history_store,
            vector_store=vector_store,
            summarizer=summarizer,
            system_prompt=system_prompt
        )

        self.tools = tools
        self.max_steps = max_steps
        self.current_session_id = None

    async def call_tool_via_router(self, tool_name: str, tool_args: dict) -> str:
        print("In call_tool_via_router")
        # Inject session_id into tool arguments
        if self.current_session_id:
            tool_args["session_id"] = self.current_session_id
            
        fast_api_uri = os.getenv("FASTAPI_URI")
        url = f"{fast_api_uri}/tools/run"
        print(f"Sending request to {url}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json={"tool_name": tool_name, "args": tool_args})

        response.raise_for_status()
        return response.json()
    
    @retry_on_rate_limit_async(
        max_attempts=5,
        wait_seconds=1,
        retry_on=sdkerror.SDKError
    )
    async def call_mistral_with_retry(self, messages):
        print("Calling mistral")
        response = await self.client.chat.complete_async(
            model=self.model,
            messages=messages,
            tools=self.tools,
        )
        return response

    async def run(self, input_data: str, session_id: str) -> str:
        # Store the current session_id
        self.current_session_id = session_id
        
        # Get the hybrid context, now including the user query for RAG
        llm_context = await self.context_manager.get_context(session_id, user_query=input_data)
        llm_context.append({"role": "user", "content": input_data})

        # Keep track of new messages for this turn to append to full history
        new_messages_this_turn = [{"role": "user", "content": input_data}]

        for step in range(self.max_steps):
            print(f"Step {step+1}")
            response = await self.call_mistral_with_retry(messages=llm_context)
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
                    result = await self.call_tool_via_router(tool_name, tool_args)
                    print(result)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": result
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