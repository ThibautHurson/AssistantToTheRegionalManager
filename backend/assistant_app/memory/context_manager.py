import json
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from backend.assistant_app.memory.vector_stores.faiss_vector_store import VectorStoreManager
from backend.assistant_app.memory.summarizer import SummarizationManager
from backend.assistant_app.memory.prompt_selector import HybridPromptSelector

class HybridContextManager:
    def __init__(
        self,
        history_store: RedisHistoryStore,
        vector_store: VectorStoreManager,
        summarizer: SummarizationManager,
        mcp_session=None,
        short_term_memory_size: int = 10,
        summary_update_interval: int = 20  # Number of messages before updating summary
    ):
        self.history_store = history_store
        self.vector_store = vector_store
        self.summarizer = summarizer
        self.mcp_session = mcp_session
        self.short_term_memory_size = short_term_memory_size
        self.summary_update_interval = summary_update_interval
        
        # Initialize prompt selector
        self.prompt_selector = HybridPromptSelector()

    def _get_summary_key(self, session_id: str) -> str:
        return f"summary:{session_id}"

    async def build_dynamic_system_prompt(self, user_query: str = "") -> str:
        """Build a dynamic system prompt using MCP prompts and semantic selection."""
        base_prompt = ""
        
        # Always include the base system prompt using MCP prompt method
        if self.mcp_session:
            try:
                result = await self.mcp_session.get_prompt("system_base")
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
        else:
            base_prompt = "You are an intelligent personal assistant that helps users manage their tasks and emails."
        
        # Use semantic prompt selector to find relevant prompts
        contextual_prompts = []
        if user_query.strip() and self.mcp_session:
            selected_prompts = self.prompt_selector.select_prompts(
                user_query, 
                use_semantic=True, 
                use_keywords=False
            )
            
            # Fetch selected prompts from MCP
            for prompt_name in selected_prompts:
                try:
                    result = await self.mcp_session.get_prompt(prompt_name)
                    if result.messages and len(result.messages) > 0:
                        content = result.messages[0].content
                        if hasattr(content, 'text'):
                            contextual_prompts.append(content.text)
                        else:
                            contextual_prompts.append(str(content))
                except Exception as e:
                    print(f"Could not fetch {prompt_name} prompt: {e}")
        
        # Combine all prompts
        all_prompts = [base_prompt] + contextual_prompts
        return "\n\n".join(all_prompts)

    async def get_context(self, session_id: str, user_query: str) -> list[dict]:
        """
        Builds a complete hybrid context for the LLM including dynamic system prompt.
        """
        context = []
        
        # 1. Build and add dynamic system prompt first
        system_prompt = await self.build_dynamic_system_prompt(user_query)
        if system_prompt:
            context.append({"role": "system", "content": system_prompt})
        
        # 2. Get current summary from Redis
        summary = self.history_store.redis.get(self._get_summary_key(session_id)) or "No summary yet."

        # 3. Get relevant historical messages from Vector Store (RAG)
        rag_msg = self.vector_store.search(user_query, k=3)
        
        # 4. Get recent messages (short-term memory)
        # Fetch a larger chunk for alignment
        full_recent_history = self.history_store.get_history(session_id, self.short_term_memory_size * 3)
        recent_messages = self.history_store.get_history(session_id, self.short_term_memory_size)
        recent_messages = self._fix_tool_message_alignment(recent_messages, full_recent_history)

        # 5. Assemble the informational context for the 'assistant' to consider
        informational_context = (
            f"--- Conversation Summary ---\n{summary}\n\n"
            f"--- Relevant Historical Messages (from long-term memory) ---\n"
        )
        if rag_msg:
            informational_context += "\n".join(f"- {msg}" for msg in rag_msg)
        else:
            informational_context += "No specific relevant information found in long-term memory."

        # Add informational context as a user message
        context.append({"role": "user", "content": f"Please use the following context to inform your response:\n{informational_context}"})
        
        # 6. Add the recent, sequential conversation history
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