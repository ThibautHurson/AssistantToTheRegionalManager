from mistralai import Mistral
import os
from dotenv import load_dotenv
import json
import httpx

from backend.assistant_app.agents.base_agent import BaseAgent
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from backend.assistant_app.agents.prompts.prompt_builder import build_system_prompt
from backend.assistant_app.utils.handle_errors import handle_httpx_errors, retry_on_rate_limit

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

    @handle_httpx_errors
    def call_tool_via_router(self, tool_name: str, tool_args: dict) -> str:
        redirect_uri = os.getenv("REDIRECT_URI")
        url = f"{redirect_uri}tools/run"
        response = httpx.post(url, json={"tool_name": tool_name, "args": tool_args})
        return response
    
    @retry_on_rate_limit(max_attempts=5, wait_seconds=1)
    def call_mistral_with_retry(self, messages):
        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
            tools=self.tools,
        )
        return response

    def run(self, input_data: str, session_id: str) -> str:
        message_history = self.history_store.get(session_id)

        message_history.append({"role": "user", "content": input_data})

        for step in range(self.max_steps):
            response = self.call_mistral_with_retry(messages=message_history)
            message = response.choices[0].message

            # Step 1: Check if the LLM wants to call a tool
            if message.tool_calls:
                message_history.append(message.model_dump())  # Save tool call

                tool_outputs = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    result = self.call_tool_via_router(tool_name, tool_args)
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