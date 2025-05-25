from mistralai import Mistral
from backend.assistant_app.agents.base_agent import BaseAgent
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from mistralai import UserMessage
import os
from dotenv import load_dotenv

class MistralChatAgent(BaseAgent):
    def __init__(self, config=None, history_store=None):
        load_dotenv()
        super().__init__(config)
        self.config = config or {}
        self.api_key = os.getenv(self.config.get("api_key_env_var", "MISTRAL_API_KEY"))
        if not self.api_key:
            raise ValueError("Mistral API key not found in environment variables")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = self.config.get("model", "mistral-small-latest")
        self.history_store = history_store or RedisHistoryStore()

    def run(self, input_data: str, session_id: str) -> str:
        message_history = self.history_store.get(session_id)

        message_history.append({"role": "user", "content": input_data})

        response = self.client.chat.complete(
            model=self.model,
            messages=message_history,
        )
        content = response.choices[0].message.content
        message_history.append({"role": "assistant", "content": content})
        self.history_store.save(session_id=session_id, history=message_history)

        return content