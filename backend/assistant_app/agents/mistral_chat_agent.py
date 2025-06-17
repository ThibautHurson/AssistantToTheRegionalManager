from mistralai import Mistral
import os
from dotenv import load_dotenv
import json
import httpx

from backend.assistant_app.agents.base_agent import BaseAgent
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from backend.assistant_app.agents.prompts.prompt_builder import build_system_prompt
from backend.assistant_app.utils.handle_errors import retry_on_rate_limit_async
from mistralai.models import sdkerror

class MistralChatAgent(BaseAgent):
    def __init__(self, config=None, history_store=None, system_prompt=None, tools=None, max_steps=5):
        load_dotenv()
        super().__init__(config)
        self.config = config or {}
        self.api_key = os.getenv(self.config.get("api_key_env_var", "MISTRAL_API_KEY"))
        if not self.api_key:
            raise ValueError("Mistral API key not found in environment variables")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = self.config.get("model", "mistral-small-latest")
        self.history_store = history_store or RedisHistoryStore()
        self.system_prompt = system_prompt or build_system_prompt()
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
        
        message_history = self.history_store.get(session_id)
        message_history.append({"role": "user", "content": input_data})

        for step in range(self.max_steps):
            print(f"Step {step+1}")
            response = await self.call_mistral_with_retry(messages=message_history)
            message = response.choices[0].message

            # Step 1: Check if the LLM wants to call a tool
            if message.tool_calls:
                message_history.append(message.model_dump())  # Save tool call

                tool_outputs = []
                for tool_call in message.tool_calls:
                    print(f"Tool chosen by Mistral: {tool_call.function.name}")
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

                message_history.extend(tool_outputs)
                continue  # Go to next LLM step with tool outputs

            # Step 2: LLM gives a final answer (no tools)
            else:
                content = message.content
                message_history.append({"role": "assistant", "content": content})
                self.history_store.save(session_id=session_id, history=message_history)
                print(message_history)
                return content

        return content