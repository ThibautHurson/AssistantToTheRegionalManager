import json
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore
from backend.assistant_app.memory.faiss_vector_store import VectorStoreManager
from backend.assistant_app.memory.summarizer import SummarizationManager
from backend.assistant_app.memory.prompt_selector import HybridPromptSelector

class HybridContextManager:
    def __init__(
        self,
        vector_store: VectorStoreManager = None,
        history_store: RedisHistoryStore = RedisHistoryStore(),
        summarizer: SummarizationManager = SummarizationManager(),
        mcp_session=None,
        user_id: str = None,
        short_term_memory_size: int = 10,
        summary_update_interval: int = 20  # Number of messages before updating summary
    ):
        self.vector_store = vector_store or VectorStoreManager(user_id=user_id)
        self.history_store = history_store
        self.summarizer = summarizer
        self.mcp_session = mcp_session
        self.short_term_memory_size = short_term_memory_size
        self.summary_update_interval = summary_update_interval
        self.user_id = user_id
        # Initialize prompt selector
        self.prompt_selector = HybridPromptSelector()

    def _get_summary_key(self, session_id: str) -> str:
        return f"summary:{session_id}"

    def _extract_text_from_mcp_prompt(self, result) -> str:
        """Extract clean text content from MCP prompt response."""
        try:
            # Handle GetPromptResult objects (MCP client response)
            if hasattr(result, 'messages') and result.messages:
                message = result.messages[0]
                if hasattr(message, 'content'):
                    content = message.content
                    if hasattr(content, 'text'):
                        return content.text
                    elif isinstance(content, dict) and 'text' in content:
                        return content['text']
                    else:
                        return str(content)

            # If result is already a string, return it directly
            if isinstance(result, str):
                return result

            return ""
        except Exception as e:
            print(f"Error extracting text from MCP prompt: {e}")
            return ""

    async def build_dynamic_system_prompt(self, user_query: str = "") -> str:
        """Build a dynamic system prompt using MCP prompts and semantic selection."""
        base_prompt = ""

        # Always include the base system prompt using MCP prompt method
        if self.mcp_session:
            try:
                result = await self.mcp_session.get_prompt("system_base")
                base_prompt = self._extract_text_from_mcp_prompt(result.messages[0].content)
                if not base_prompt:
                    base_prompt = "You are an intelligent personal assistant that helps users manage their tasks and emails."
            except Exception as e:
                print(f"Could not fetch system_base prompt: {e}")
                base_prompt = "You are an intelligent personal assistant that helps users manage their tasks and emails."
        else:
            base_prompt = "You are an intelligent personal assistant that helps users manage their tasks and emails."

        # Add current datetime information to the base prompt
        try:
            from datetime import datetime
            current_datetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            datetime_info = f"\n\n**CURRENT DATETIME:** {current_datetime}\n\n"

            base_prompt += datetime_info
        except Exception as e:
            print(f"Could not add current datetime info: {e}")

        # Use semantic prompt selector to find relevant prompts
        contextual_prompts = []
        if user_query.strip() and self.mcp_session:
            selected_prompts = self.prompt_selector.select_prompts(
                user_query,
                use_semantic=True,
                use_keywords=False
            )

            # Fetch selected prompts from MCP and extract clean text content
            for prompt_name in selected_prompts:
                try:
                    result = await self.mcp_session.get_prompt(prompt_name)
                    prompt_text = self._extract_text_from_mcp_prompt(result.messages[0].content)
                    if prompt_text:
                        contextual_prompts.append(prompt_text)
                except Exception as e:
                    print(f"Could not fetch {prompt_name} prompt: {e}")

        # Combine all prompts
        all_prompts = [base_prompt] + contextual_prompts
        return "\n\n".join(all_prompts)

    async def get_context(self, session_id: str, user_query: str) -> list[dict]:
        """
        Builds a complete hybrid context for the LLM including dynamic system prompt.
        """
        print(f"Getting context for session_id: {session_id}")
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

        print(f"Found {len(recent_messages)} recent messages for session {session_id}")

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

        # Final validation: Ensure no malformed tool call sequences
        context = self._validate_context_integrity(context)
        return context

    async def save_new_messages(self, session_id: str, new_messages: list[dict]):
        """
        Saves new messages and updates long-term memory structures.
        """
        print(f"Saving {len(new_messages)} new messages for session_id: {session_id}")

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

    def _validate_context_integrity(self, context: list[dict]) -> list[dict]:
        """
        Validates that the context doesn't contain malformed tool call sequences.
        This is a final safety check to prevent function call mismatches.
        """
        validated_context = []
        i = 0

        while i < len(context):
            msg = context[i]

            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Check if we have the corresponding tool responses
                tool_calls = msg["tool_calls"]
                tool_call_ids = set(tc.get("id") for tc in tool_calls)

                # Look ahead for tool responses
                responses_found = set()
                j = i + 1
                while j < len(context) and context[j].get("role") == "tool":
                    tool_response = context[j]
                    response_id = tool_response.get("tool_call_id")
                    if response_id in tool_call_ids:
                        responses_found.add(response_id)
                    j += 1

                # Only include if we have all tool responses
                if len(responses_found) == len(tool_call_ids):
                    validated_context.append(msg)
                    # Add all tool responses
                    for k in range(i + 1, j):
                        validated_context.append(context[k])
                    i = j
                else:
                    # Skip this assistant message AND all following tool responses to avoid orphaned tools
                    print(f"Warning: Skipping assistant message with incomplete tool responses")
                    print(f"Expected {len(tool_call_ids)} responses, found {len(responses_found)}")
                    # Skip to after all tool responses to avoid orphaned tools
                    while j < len(context) and context[j].get("role") == "tool":
                        j += 1
                    i = j
            elif msg.get("role") == "tool":
                # Skip orphaned tool responses (they should only appear after assistant messages with tool_calls)
                print(f"Warning: Skipping orphaned tool response")
                i += 1
            else:
                validated_context.append(msg)
                i += 1

        return validated_context

    def clear_user_data(self):
        """Clear memory-related user data (vector store and Redis).
        For complete user data deletion including tasks, use UserDataService."""
        print(f"Starting memory data deletion for user: {self.user_id}")

        # Clear vector store data
        self.vector_store.clear_user_data()

        # Clear Redis history data
        deleted_count = self.history_store.delete_history(self.user_id)

        print(f"Completed memory data deletion for user: {self.user_id}")
        print(f"- Vector store: Cleared")
        print(f"- Redis keys: {deleted_count} deleted")

        return {
            "user_id": self.user_id,
            "vector_store_cleared": True,
            "redis_keys_deleted": deleted_count,
        }