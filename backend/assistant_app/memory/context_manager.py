import json
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from backend.assistant_app.memory.vector_stores.faiss_vector_store import VectorStoreManager
from backend.assistant_app.memory.summarizer import SummarizationManager

class HybridContextManager:
    def __init__(
        self,
        history_store: RedisHistoryStore,
        vector_store: VectorStoreManager,
        summarizer: SummarizationManager,
        system_prompt: str = None,
        short_term_memory_size: int = 10,
        summary_update_interval: int = 20  # Number of messages before updating summary
    ):
        self.history_store = history_store
        self.vector_store = vector_store
        self.summarizer = summarizer
        self.system_prompt = system_prompt
        self.short_term_memory_size = short_term_memory_size
        self.summary_update_interval = summary_update_interval

    def _get_summary_key(self, session_id: str) -> str:
        return f"summary:{session_id}"

    async def get_context(self, session_id: str, user_query: str) -> list[dict]:
        """
        Builds a hybrid context for the LLM.
        """
        # 1. Get current summary from Redis
        summary = self.history_store.redis.get(self._get_summary_key(session_id)) or "No summary yet."

        # 2. Get relevant documents from Vector Store (RAG)
        rag_docs = self.vector_store.search(user_query, k=3)
        
        # 3. Get recent messages (short-term memory)
        # Fetch a larger chunk for alignment
        full_recent_history = self.history_store.get_history(session_id, self.short_term_memory_size * 3)
        recent_messages = self.history_store.get_history(session_id, self.short_term_memory_size)
        recent_messages = self._fix_tool_message_alignment(recent_messages, full_recent_history)

        # 4. Construct the context prompt
        context = []
        if self.system_prompt:
            context.append({"role": "system", "content": self.system_prompt})

        # Assemble the informational context for the 'assistant' to consider
        informational_context = (
            f"--- Conversation Summary ---\n{summary}\n\n"
            f"--- Relevant Information (from long-term memory) ---\n"
        )
        if rag_docs:
            informational_context += "\n".join(f"- {doc}" for doc in rag_docs)
        else:
            informational_context += "No specific relevant information found in long-term memory."

        # We'll inject this combined context as a single 'system' or 'user' message
        # before the main conversation history starts.
        # Note: Using a 'user' role for this might be more effective with some models.
        context.append({"role": "user", "content": f"Please use the following context to inform your response:\n{informational_context}"})
        
        # Add the recent, sequential conversation history
        context.extend(recent_messages)

        return context

    async def save_new_messages(self, session_id: str, new_messages: list[dict]):
        """
        Saves new messages and updates long-term memory structures.
        """
        # 1. Save new messages to Redis list (short-term memory)
        self.history_store.append_messages(session_id, new_messages)
        
        # 2. Add new messages to the Vector Store
        # We only want to embed user and assistant text content, not tool calls/responses
        docs_to_embed = [
            f"{msg['role']}: {msg['content']}" 
            for msg in new_messages 
            if msg.get('content') and msg.get('role') in ['user', 'assistant']
        ]
        if docs_to_embed:
            self.vector_store.add_documents(docs_to_embed)

        # 3. Periodically update the summary
        total_messages = self.history_store.redis.llen(session_id)
        if total_messages % self.summary_update_interval == 0:
            await self._update_summary(session_id, total_messages)

    async def _update_summary(self, session_id: str, total_messages: int):
        """
        Updates the conversation summary.
        """
        print(f"Updating summary for session {session_id}...")
        # Get the current summary
        summary_key = self._get_summary_key(session_id)
        current_summary = self.history_store.redis.get(summary_key) or ""

        # Get the messages that have not yet been summarized
        # This logic assumes we summarize in chunks of `summary_update_interval`
        # and appends to the existing summary.
        num_new_msgs = self.summary_update_interval
        # Fetch from the list, starting from the beginning of the new chunk
        new_chunk_start_index = -num_new_msgs 
        raw_new_messages = self.history_store.redis.lrange(session_id, new_chunk_start_index, -1)
        new_messages_to_summarize = [json.loads(msg) for msg in raw_new_messages]

        # Create a combined text for the new summary
        text_to_summarize = f"Previous summary:\n{current_summary}\n\nNew conversation turns:\n"
        text_to_summarize += "\n".join(
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" 
            for msg in new_messages_to_summarize if msg.get('content')
        )

        # Generate new summary
        new_summary = await self.summarizer.summarize_conversation([{"role": "user", "content": text_to_summarize}])

        # Save the updated summary to Redis
        if "Error" not in new_summary:
            self.history_store.redis.set(summary_key, new_summary)
            print(f"Summary for session {session_id} updated.")

    def _fix_tool_message_alignment(self, messages: list[dict], full_history: list[dict]) -> list[dict]:
        # If the first message is a tool, prepend its parent assistant message from full_history
        if messages and messages[0].get("role") == "tool":
            # Find the index of this message in the full history
            first_tool_call_id = messages[0].get("tool_call_id")
            for i in range(len(full_history)):
                msg = full_history[i]
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    for tool_call in msg["tool_calls"]:
                        if tool_call.get("id") == first_tool_call_id:
                            # Prepend the parent assistant message
                            return [msg] + messages
            # If not found, skip the orphaned tool message
            return messages[1:]
        return messages 