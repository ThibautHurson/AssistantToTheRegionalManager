from unittest.mock import Mock, patch, AsyncMock
import pytest
from backend.assistant_app.agents.mistral_chat_agent import MistralMCPChatAgent


class TestMistralMCPChatAgent:
    """Test cases for MistralMCPChatAgent."""

    @pytest.fixture
    def agent(self):
        """Create a MistralMCPChatAgent instance for testing."""
        with patch('backend.assistant_app.agents.mistral_chat_agent.Mistral'):
            return MistralMCPChatAgent()

    @pytest.fixture
    def mock_mistral_client(self):
        """Create a mock Mistral client."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_client.chat.complete_async.return_value = mock_response
        return mock_client

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    def test_agent_initialization(self, mock_mistral):
        """Test agent initialization."""
        mock_client = Mock()
        mock_mistral.return_value = mock_client

        agent = MistralMCPChatAgent()

        assert agent.model == "mistral-small-latest"
        assert agent.max_steps == 5
        assert agent.current_session_id is None
        assert agent.session is None
        assert agent.mcp_tools == []

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    def test_agent_initialization_no_api_key(self, mock_mistral):
        """Test agent initialization without API key."""
        # Clear the environment variable completely
        with patch.dict('os.environ', {}, clear=True):
            with patch('os.getenv', return_value=None):
                with pytest.raises(ValueError, match="Mistral API key not found"):
                    MistralMCPChatAgent()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_connect_to_server_success(self, mock_mistral, agent):
        """Test successful server connection."""
        # Mock the exit stack and stdio client
        mock_transport = (Mock(), Mock())  # (stdio, write)
        mock_session = Mock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()

        with patch.object(agent.exit_stack, 'enter_async_context') as mock_enter:
            mock_enter.side_effect = [mock_transport, mock_session]

            # Mock the list_tools response
            mock_tools_response = Mock()
            mock_tool1 = Mock()
            mock_tool1.name = "tool1"
            mock_tool1.description = "Tool 1"
            mock_tool2 = Mock()
            mock_tool2.name = "tool2"
            mock_tool2.description = "Tool 2"
            mock_tools_response.tools = [mock_tool1, mock_tool2]
            mock_session.list_tools.return_value = mock_tools_response

            await agent.connect_to_server("test_server.py")

            # Verify session was initialized
            mock_session.initialize.assert_called_once()
            mock_session.list_tools.assert_called_once()
            assert len(agent.mcp_tools) == 2
            assert agent.mcp_tools[0].name == "tool1"
            assert agent.mcp_tools[1].name == "tool2"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_connect_to_server_invalid_file(self, mock_mistral, agent):
        """Test server connection with invalid file type."""
        with pytest.raises(ValueError, match="Server script must be a .py or .js file"):
            await agent.connect_to_server("test_server.txt")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_connect_to_fetch_server_success(self, mock_mistral, agent):
        """Test successful fetch server connection."""
        # Mock the fetch server connection
        mock_fetch_transport = (Mock(), Mock())
        mock_fetch_session = Mock()
        mock_fetch_session.initialize = AsyncMock()
        mock_fetch_session.list_tools = AsyncMock()

        with patch.object(agent.exit_stack, 'enter_async_context') as mock_enter:
            mock_enter.side_effect = [mock_fetch_transport, mock_fetch_session]

            # Mock the fetch tools response
            mock_fetch_response = Mock()
            mock_fetch_tool = Mock()
            mock_fetch_tool.name = "fetch"
            mock_fetch_tool.description = "Fetch tool"
            mock_fetch_response.tools = [mock_fetch_tool]
            mock_fetch_session.list_tools.return_value = mock_fetch_response

            await agent.connect_to_fetch_server()

            # Verify fetch session was initialized
            mock_fetch_session.initialize.assert_called_once()
            mock_fetch_session.list_tools.assert_called_once()
            assert len(agent.mcp_tools) == 1
            assert agent.mcp_tools[0].name == "fetch"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_connect_to_fetch_server_failure(self, mock_mistral, agent):
        """Test fetch server connection failure."""
        with patch.object(agent.exit_stack, 'enter_async_context') as mock_enter:
            mock_enter.side_effect = Exception("Connection failed")

            await agent.connect_to_fetch_server()

            # Should handle error gracefully
            assert agent.fetch_session is None

    @pytest.mark.unit
    def test_cleanup_source_references(self, agent):
        """Test source reference cleaning."""
        # Test with [REF] tags
        content = "Here is some information [REF]tool1[/REF] and more text"
        result = agent._cleanup_source_references(content)

        assert "[REF]" not in result
        assert "[/REF]" not in result
        assert "Here is some information" in result
        assert "and more text" in result

    @pytest.mark.unit
    def test_cleanup_source_references_with_urls(self, agent):
        """Test source reference cleaning with URLs."""
        content = "Check this link: https://example.com for more info"
        result = agent._cleanup_source_references(content)

        assert "https://example.com" in result
        assert "**Sources:**" in result
        assert "Example" in result  # Domain name should be extracted

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_run_simple_chat(self, mock_mistral, agent, mock_mistral_client):
        """Test simple chat without tool calls."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context_manager.get_context = AsyncMock()
        mock_context_manager.get_context.return_value = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"}
        ]
        mock_context_manager.save_new_messages = AsyncMock()

        with patch('backend.assistant_app.agents.mistral_chat_agent.HybridContextManager') \
                as mock_cm:
            mock_cm.return_value = mock_context_manager

            # Mock the LLM response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Hello! How can I help you?"
            mock_response.choices[0].message.tool_calls = None
            mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)

            with patch.object(agent, 'client', mock_mistral_client):
                result = await agent.run("Hello", "session123",
                                       "test@example.com")

                assert result == "Hello! How can I help you?"
                mock_context_manager.save_new_messages.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_run_with_tool_calls(self, mock_mistral, agent, mock_mistral_client):
        """Test chat with tool calls."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context_manager.get_context = AsyncMock()
        mock_context_manager.get_context.return_value = [
            {"role": "system", "content": "You are a helpful assistant"}
        ]
        mock_context_manager.save_new_messages = AsyncMock()

        with patch('backend.assistant_app.agents.mistral_chat_agent.HybridContextManager') \
                as mock_cm:
            mock_cm.return_value = mock_context_manager

            # Mock the session for tool calls
            agent.session = Mock()
            agent.session.call_tool = AsyncMock()
            agent.session.call_tool.return_value = Mock(content="Tool result")

            # Mock the LLM responses
            # First response with tool call
            mock_response1 = Mock()
            mock_response1.choices = [Mock()]
            mock_response1.choices[0].message = Mock()
            mock_response1.choices[0].message.content = None
            mock_tool_call = Mock()
            mock_tool_call.id = "call1"
            mock_tool_call.function = Mock()
            mock_tool_call.function.name = "test_tool"
            mock_tool_call.function.arguments = '{"param": "value"}'
            mock_response1.choices[0].message.tool_calls = [mock_tool_call]

            # Second response with final answer
            mock_response2 = Mock()
            mock_response2.choices = [Mock()]
            mock_response2.choices[0].message = Mock()
            mock_response2.choices[0].message.content = ("Based on the tool result, "
                                                         "here's the answer")
            mock_response2.choices[0].message.tool_calls = None

            mock_mistral_client.chat.complete_async = AsyncMock(side_effect=[mock_response1,
                                                                             mock_response2])

            with patch.object(agent, 'client', mock_mistral_client):
                result = await agent.run("Use the test tool", "session123",
                                       "test@example.com")

                assert "Based on the tool result" in result
                # The tool call should have been made with the correct arguments
                agent.session.call_tool.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_run_with_tool_error(self, mock_mistral, agent, mock_mistral_client):
        """Test chat with tool call error."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context_manager.get_context = AsyncMock()
        mock_context_manager.get_context.return_value = [
            {"role": "system", "content": "You are a helpful assistant"}
        ]
        mock_context_manager.save_new_messages = AsyncMock()

        with patch('backend.assistant_app.agents.mistral_chat_agent.HybridContextManager') \
                as mock_cm:
            mock_cm.return_value = mock_context_manager

            # Mock the session for tool calls
            agent.session = Mock()
            agent.session.call_tool = AsyncMock()
            agent.session.call_tool.side_effect = Exception("Tool error")
            agent.session.get_prompt = AsyncMock()
            agent.session.get_prompt.return_value = Mock(
                messages=[Mock(content=Mock(text="Provide helpful error recovery suggestions."))]
            )

            # Mock the LLM responses
            mock_response1 = Mock()
            mock_response1.choices = [Mock()]
            mock_response1.choices[0].message = Mock()
            mock_response1.choices[0].message.content = None
            mock_tool_call = Mock()
            mock_tool_call.id = "call1"
            mock_tool_call.function = Mock()
            mock_tool_call.function.name = "test_tool"
            mock_tool_call.function.arguments = '{"param": "value"}'
            mock_response1.choices[0].message.tool_calls = [mock_tool_call]

            mock_response2 = Mock()
            mock_response2.choices = [Mock()]
            mock_response2.choices[0].message = Mock()
            mock_response2.choices[0].message.content = "I'll help you with an alternative approach"
            mock_response2.choices[0].message.tool_calls = None

            mock_mistral_client.chat.complete_async = AsyncMock(side_effect=[mock_response1,
                                                                             mock_response2])

            with patch.object(agent, 'client', mock_mistral_client):
                result = await agent.run("Use the test tool", "session123",
                                       "test@example.com")

                assert "alternative approach" in result
                # Should have called get_prompt for error handling
                agent.session.get_prompt.assert_called_once_with("error_handling")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_run_max_steps_reached(self, mock_mistral, agent, mock_mistral_client):
        """Test chat when max steps are reached."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context_manager.get_context = AsyncMock()
        mock_context_manager.get_context.return_value = [
            {"role": "system", "content": "You are a helpful assistant"}
        ]
        mock_context_manager.save_new_messages = AsyncMock()

        with patch('backend.assistant_app.agents.mistral_chat_agent.HybridContextManager') \
                as mock_cm:
            mock_cm.return_value = mock_context_manager

            # Mock the session for tool calls
            agent.session = Mock()
            agent.session.call_tool = AsyncMock()
            agent.session.call_tool.return_value = Mock(content="Tool result")

            # Mock the LLM to always return tool calls (exceeding max steps)
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = None
            mock_tool_call = Mock()
            mock_tool_call.id = "call1"
            mock_tool_call.function = Mock()
            mock_tool_call.function.name = "test_tool"
            mock_tool_call.function.arguments = '{"param": "value"}'
            mock_response.choices[0].message.tool_calls = [mock_tool_call]
            mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)

            with patch.object(agent, 'client', mock_mistral_client):
                result = await agent.run("Use the test tool", "session123", "test@example.com")

                # After max steps, should return the last tool result
                assert "Tool result" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_cleanup(self, mock_mistral, agent):
        """Test agent cleanup."""
        # Mock the exit stack
        mock_exit_stack = Mock()
        mock_exit_stack.aclose = AsyncMock()
        agent.exit_stack = mock_exit_stack

        await agent.cleanup()

        mock_exit_stack.aclose.assert_called_once()

    @pytest.mark.unit
    def test_clear_user_data(self, agent):
        """Test clearing user data."""
        with patch('backend.assistant_app.services.user_data_service.UserDataService') \
                as mock_service:
            mock_user_data_service = Mock()
            mock_user_data_service.clear_user_data.return_value = {
                "success": True,
                "vector_store_cleared": True,
                "redis_keys_deleted": 5,
                "database_tasks_deleted": 3
            }
            mock_service.return_value = mock_user_data_service

            result = agent.clear_user_data("test@example.com")

            assert result["success"] is True
            assert result["vector_store_cleared"] is True
            assert result["redis_keys_deleted"] == 5
            assert result["database_tasks_deleted"] == 3

    @pytest.mark.unit
    def test_cleanup_source_references_complex(self, agent):
        """Test complex source reference cleaning."""
        content = """
        Here is some information [REF]tool1[/REF] and more text.
        Check these links: https://example.com and https://test.org
        More content here.
        """

        result = agent._cleanup_source_references(content)

        # Should remove [REF] tags
        assert "[REF]" not in result
        assert "[/REF]" not in result

        # Should add Sources section
        assert "**Sources:**" in result
        assert "https://example.com" in result
        assert "https://test.org" in result

        # Should preserve original content
        assert "Here is some information" in result
        assert "More content here" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.mistral_chat_agent.Mistral')
    async def test_run_with_fetch_tools(self, mock_mistral, agent, mock_mistral_client):
        """Test chat with fetch tools."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context_manager.get_context = AsyncMock()
        mock_context_manager.get_context.return_value = [
            {"role": "system", "content": "You are a helpful assistant"}
        ]
        mock_context_manager.save_new_messages = AsyncMock()

        with patch('backend.assistant_app.agents.mistral_chat_agent.HybridContextManager') \
                as mock_cm:
            mock_cm.return_value = mock_context_manager

            # Mock the fetch session
            agent.fetch_session = Mock()
            agent.fetch_session.call_tool = AsyncMock()
            agent.fetch_session.call_tool.return_value = Mock(content="Fetch result")

            # Mock the LLM responses
            mock_response1 = Mock()
            mock_response1.choices = [Mock()]
            mock_response1.choices[0].message = Mock()
            mock_response1.choices[0].message.content = None
            mock_tool_call = Mock()
            mock_tool_call.id = "call1"
            mock_tool_call.function = Mock()
            mock_tool_call.function.name = "fetch"
            mock_tool_call.function.arguments = '{"url": "https://example.com"}'
            mock_response1.choices[0].message.tool_calls = [mock_tool_call]

            mock_response2 = Mock()
            mock_response2.choices = [Mock()]
            mock_response2.choices[0].message = Mock()
            mock_response2.choices[0].message.content = "Based on the fetched content..."
            mock_response2.choices[0].message.tool_calls = None

            mock_mistral_client.chat.complete_async = AsyncMock(side_effect=[mock_response1,
                                                                             mock_response2])

            with patch.object(agent, 'client', mock_mistral_client):
                result = await agent.run("Fetch some content", "session123", "test@example.com")

                assert "Based on the fetched content" in result
                # Should use fetch session for fetch tools
                agent.fetch_session.call_tool.assert_called_once()
