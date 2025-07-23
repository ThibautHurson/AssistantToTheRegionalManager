import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('backend.assistant_app.memory.redis_history_store.redis.Redis') as mock_redis:
        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance
        yield mock_redis_instance
@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    with patch('backend.assistant_app.memory.faiss_vector_store.VectorStoreManager') as mock_vs:
        mock_instance = Mock()
        mock_vs.return_value = mock_instance
        yield mock_instance
@pytest.fixture
def mock_task_manager():
    """Mock task manager for testing."""
    with patch('backend.assistant_app.models.task_manager.TaskManager') as mock_tm:
        mock_instance = Mock()
        mock_tm.return_value = mock_instance
        yield mock_instance
@pytest.fixture
def sample_user_email():
    """Sample user email for testing."""
    return "test@example.com"
@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "test_session_123"
@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            "id": "task_1",
            "title": "Test Task 1",
            "description": "Test description 1",
            "priority": 1,
            "status": "pending",
            "user_id": "test@example.com"
        },
        {
            "id": "task_2",
            "title": "Test Task 2",
            "description": "Test description 2",
            "priority": 2,
            "status": "completed",
            "user_id": "test@example.com"
        }
    ]
@pytest.fixture
def mock_faiss_index():
    """Mock FAISS index for testing."""
    with patch('backend.assistant_app.memory.faiss_vector_store.faiss') as mock_faiss:
        mock_index = Mock()
        mock_faiss.IndexFlatL2.return_value = mock_index
        mock_faiss.read_index.return_value = mock_index
        yield mock_index
@pytest.fixture
def mock_sentence_transformer():
    """Mock sentence transformer for testing."""
    with patch('backend.assistant_app.memory.faiss_vector_store.SentenceTransformer') as mock_st:
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = [[0.1] * 384]  # Mock embeddings
        mock_st.return_value = mock_model
        yield mock_model
@pytest.fixture
def sample_conversation_messages():
    """Sample conversation messages for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with a task?"},
        {"role": "assistant", "content": "Of course! What do you need help with?"}
    ]
@pytest.fixture
def mock_context_manager():
    """Mock context manager for testing."""
    with patch('backend.assistant_app.memory.context_manager.HybridContextManager') as mock_cm:
        mock_instance = Mock()
        mock_cm.return_value = mock_instance
        yield mock_instance
@pytest.fixture
def mock_auth_service():
    """Mock auth service for testing."""
    with patch('backend.assistant_app.services.auth_service.auth_service') as mock_auth:
        yield mock_auth
@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "session_token": "valid_session_token_123"
    }
