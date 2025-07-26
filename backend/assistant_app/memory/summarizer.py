import os
from dotenv import load_dotenv
from mistralai import Mistral
from backend.assistant_app.utils.logger import error_logger

load_dotenv()

class SummarizationManager:
    def __init__(self, model_name="mistral-small-latest"):
        self.api_key = os.getenv("MISTRAL_KEY")
        if not self.api_key:
            raise ValueError("Mistral API key not found in environment variables")
        self.client = Mistral(api_key=self.api_key)
        self.model = model_name

    async def summarize_conversation(self, messages: list[dict]) -> str:
        if not messages:
            return ""

        # Format messages into a single string
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in messages
        )

        prompt = f"""
        Please provide a concise summary of the following conversation.
        The summary should capture the key points, decisions, and action items.
        Do not add any preamble like "Here is the summary". Just provide the summary directly.

        Conversation:
        ---
        {conversation_text}
        ---
        """

        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_logger.log_error(e, {"context": "summarization"})
            return f"Error summarizing conversation: {e}"
