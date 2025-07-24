from unittest.mock import Mock, patch, AsyncMock

import pytest
from backend.assistant_app.memory.context_manager import HybridContextManager
from backend.assistant_app.memory.faiss_vector_store import VectorStoreManager
from backend.assistant_app.memory.redis_history_store import RedisHistoryStore


class TestHybridContextManager:
    """Test cases for HybridContextManager."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        mock_vs = Mock(spec=VectorStoreManager)
        mock_vs.search.return_value = ["relevant message 1", "relevant message 2"]
        mock_vs.add_documents.return_value = None
        return mock_vs

    @pytest.fixture
    def mock_history_store(self):
        """Create a mock history store."""
        mock_hs = Mock(spec=RedisHistoryStore)
        mock_hs.get_history.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        mock_hs.append_messages.return_value = None
        mock_hs.redis = Mock()
        mock_hs.redis.get.return_value = "Previous conversation summary"
        mock_hs.redis.llen.return_value = 10
        mock_hs.redis.lrange.return_value = [
            '{"role": "user", "content": "New message"}',
            '{"role": "assistant", "content": "Response"}'
        ]
        return mock_hs

    @pytest.fixture
    def mock_summarizer(self):
        """Create a mock summarizer."""
        mock_sum = Mock()
        mock_sum.summarize_conversation.return_value = "Updated summary"
        return mock_sum

    @pytest.fixture
    def mock_mcp_session(self):
        """Create a mock MCP session."""
        mock_session = Mock()
        mock_session.get_prompt = AsyncMock()
        mock_session.get_prompt.return_value = Mock()
        mock_session.get_prompt.return_value.messages = [Mock()]
        mock_session.get_prompt.return_value.messages[0].content = Mock()
        mock_session.get_prompt.return_value.messages[0].content.text = "System base prompt"
        return mock_session

    @pytest.fixture
    def context_manager(self, mock_vector_store, mock_history_store,
                       mock_summarizer, mock_mcp_session):
        """Create a HybridContextManager instance for testing."""
        return HybridContextManager(
            vector_store=mock_vector_store,
            history_store=mock_history_store,
            summarizer=mock_summarizer,
            mcp_session=mock_mcp_session,
            user_id="test@example.com"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_build_dynamic_system_prompt_success(self, context_manager, mock_mcp_session):
        """Test successful dynamic system prompt building."""
        # Mock the prompt selector
        with patch.object(context_manager.prompt_selector, 'select_prompts') as mock_select:
            mock_select.return_value = ["productivity_coach", "task_management"]

            result = await context_manager.build_dynamic_system_prompt("Help me with tasks")

            # Should contain the base prompt and current datetime
            assert "intelligent personal assistant" in result
            assert "CURRENT DATETIME" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_build_dynamic_system_prompt_no_mcp_session(self):
        """Test system prompt building without MCP session."""
        context_manager = HybridContextManager(user_id="test@example.com")

        result = await context_manager.build_dynamic_system_prompt("Help me")

        assert "intelligent personal assistant" in result
        assert "CURRENT DATETIME" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_success(self, context_manager, mock_mcp_session):
        """Test successful context retrieval."""
        # Mock the system prompt building
        with patch.object(context_manager, 'build_dynamic_system_prompt') as mock_build:
            mock_build.return_value = "System prompt"

            result = await context_manager.get_context("session123", "user query")

            # Should contain system prompt, informational context, and recent messages
            assert len(result) > 0
            assert any(msg["role"] == "system" for msg in result)
            assert any(msg["role"] == "user" and "context" in msg["content"] for msg in result)
            assert any(msg["role"] == "user" and msg["content"] == "Hello" for msg in result)
            assert any(
                msg["role"] == "assistant" and msg["content"] == "Hi there!"
                for msg in result
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_no_vector_results(self, context_manager,
                                                 mock_vector_store,
                                                 mock_mcp_session):
        """Test context retrieval when vector store returns no results."""
        # Mock empty vector search results
        mock_vector_store.search.return_value = []

        with patch.object(context_manager, 'build_dynamic_system_prompt') as mock_build:
            mock_build.return_value = "System prompt"

            result = await context_manager.get_context("session123", "user query")

            # Should still contain system prompt and recent messages
            assert len(result) > 0
            assert any(msg["role"] == "system" for msg in result)
            assert any("No specific relevant information found" in msg["content"]
                      for msg in result)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_new_messages_success(self, context_manager, mock_vector_store):
        """Test successful message saving."""
        new_messages = [
            {"role": "user", "content": "New question"},
            {"role": "assistant", "content": "New answer"}
        ]

        await context_manager.save_new_messages("session123", new_messages)

        # Verify messages were saved to history store
        context_manager.history_store.append_messages.assert_called_once_with(
            "session123", new_messages)

        # Verify documents were added to vector store
        mock_vector_store.add_documents.assert_called_once()
        call_args = mock_vector_store.add_documents.call_args[0][0]
        assert len(call_args) == 2
        assert "user: New question" in call_args[0]
        assert "assistant: New answer" in call_args[1]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_new_messages_with_tool_calls(self, context_manager, mock_vector_store):
        """Test message saving with tool calls (should not be embedded)."""
        new_messages = [
            {"role": "user", "content": "Search for information"},
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": "call1", "function": {"name": "search"}}]},
            {"role": "tool", "content": "Search results", "tool_call_id": "call1"},
            {"role": "assistant", "content": "Based on the search results..."}
        ]

        await context_manager.save_new_messages("session123", new_messages)

        # Verify only text content was added to vector store (not tool calls)
        mock_vector_store.add_documents.assert_called_once()
        call_args = mock_vector_store.add_documents.call_args[0][0]
        assert len(call_args) == 2  # Only user and final assistant messages
        assert "user: Search for information" in call_args[0]
        assert "assistant: Based on the search results..." in call_args[1]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_summary(self, context_manager, mock_summarizer):
        """Test summary updating."""
        # Mock the summarizer as AsyncMock
        mock_summarizer.summarize_conversation = AsyncMock(return_value="Updated summary")

        # Mock the summary update interval
        context_manager.summary_update_interval = 5
        context_manager.history_store.redis.llen.return_value = 10  # Multiple of interval

        await context_manager._update_summary("session123", 10)

        # Verify summarizer was called
        mock_summarizer.summarize_conversation.assert_called_once()

        # Verify summary was saved
        context_manager.history_store.redis.set.assert_called_once()

    @pytest.mark.unit
    def test_fix_tool_message_alignment(self, context_manager):
        """Test tool message alignment fixing."""
        # Test case where first message is a tool call
        messages = [
            {"role": "tool", "content": "tool result", "tool_call_id": "call1"}
        ]
        full_history = [
            {"role": "assistant", "content": "I'll search", "tool_calls": [{"id": "call1"}]},
            {"role": "tool", "content": "tool result", "tool_call_id": "call1"}
        ]

        result = context_manager._fix_tool_message_alignment(messages, full_history)

        # Should prepend the parent assistant message
        assert len(result) == 2
        assert result[0]["role"] == "assistant"
        assert result[1]["role"] == "tool"

    @pytest.mark.unit
    def test_validate_context_integrity(self, context_manager):
        """Test context integrity validation."""
        # Test case with complete tool call sequence
        context = [
            {"role": "assistant", "content": "I'll search", "tool_calls": [{"id": "call1"}]},
            {"role": "tool", "content": "result", "tool_call_id": "call1"},
            {"role": "assistant", "content": "Based on results..."}
        ]

        result = context_manager._validate_context_integrity(context)

        # Should keep complete sequences
        assert len(result) == 3
        assert result[0]["role"] == "assistant"
        assert result[1]["role"] == "tool"
        assert result[2]["role"] == "assistant"

    @pytest.mark.unit
    def test_validate_context_integrity_incomplete_tools(self, context_manager):
        """Test context validation with incomplete tool sequences."""
        # Test case with incomplete tool call sequence
        context = [
            {"role": "assistant", "content": "I'll search",
             "tool_calls": [{"id": "call1"}, {"id": "call2"}]},
            {"role": "tool", "content": "result", "tool_call_id": "call1"},
            # Missing call2 response
            {"role": "assistant", "content": "Based on results..."}
        ]

        result = context_manager._validate_context_integrity(context)

        # Should skip incomplete sequences
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert "Based on results" in result[0]["content"]

    @pytest.mark.unit
    def test_clear_user_data(self, context_manager, mock_vector_store, mock_history_store):
        """Test clearing user data."""
        # Mock the history store delete method
        mock_history_store.delete_history.return_value = 5

        result = context_manager.clear_user_data()

        # Verify vector store was cleared
        mock_vector_store.clear_user_data.assert_called_once()

        # Verify history was deleted
        mock_history_store.delete_history.assert_called_once_with("test@example.com")

        # Verify return structure
        assert result["user_id"] == "test@example.com"
        assert result["vector_store_cleared"] is True
        assert result["redis_keys_deleted"] == 5

    @pytest.mark.unit
    def test_extract_text_from_mcp_prompt_success(self, context_manager):
        """Test successful text extraction from MCP prompt."""
        # Mock MCP result with proper structure
        mock_result = Mock()
        mock_result.messages = [Mock()]
        mock_result.messages[0].content = Mock()
        mock_result.messages[0].content.text = "Extracted text"

        result = context_manager._extract_text_from_mcp_prompt(mock_result)

        assert result == "Extracted text"

    @pytest.mark.unit
    def test_extract_text_from_mcp_prompt_string(self, context_manager):
        """Test text extraction when result is already a string."""
        result = context_manager._extract_text_from_mcp_prompt("Simple string")

        assert result == "Simple string"

    @pytest.mark.unit
    def test_extract_text_from_mcp_prompt_error(self, context_manager):
        """Test text extraction when error occurs."""
        # Mock result that will cause an error
        mock_result = Mock()
        mock_result.messages = [Mock()]
        mock_result.messages[0].content = None  # This will cause an error

        result = context_manager._extract_text_from_mcp_prompt(mock_result)

        assert result == "None"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_with_tool_calls(self, context_manager, mock_mcp_session):
        """Test context retrieval with tool calls in history."""
        # Mock history with tool calls
        context_manager.history_store.get_history.return_value = [
            {"role": "user", "content": "Search for something"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call1"}]},
            {"role": "tool", "content": "Search results", "tool_call_id": "call1"},
            {"role": "assistant", "content": "Based on the search..."}
        ]

        with patch.object(context_manager, 'build_dynamic_system_prompt') as mock_build:
            mock_build.return_value = "System prompt"

            result = await context_manager.get_context("session123", "user query")

            # Should include all messages including tool calls
            assert len(result) > 0
            assert any(msg.get("tool_calls") for msg in result)
            assert any(msg["role"] == "tool" for msg in result)
