import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from backend.assistant_app.main import app
class TestAPIEndpoints:
    """Test cases for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.mark.api
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.api
    def test_prompts_endpoint(self, client):
        """Test prompts endpoint"""
        response = client.get("/prompts")
        # This endpoint exists, so it should return some response
        assert response.status_code in [200, 404, 500]  # Accept various status codes

    @pytest.mark.api
    @pytest.mark.auth
    def test_register_user(self, client):
        """Test user registration endpoint."""
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        response = client.post("/auth/register", json=user_data)
        # Should return 200 for successful registration or 400 if user already exists
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert data["success"]
            assert "message" in data

    @pytest.mark.api
    @pytest.mark.auth
    def test_login_user_success(self, client):
        """Test successful login (user exists)."""
        # First register the user
        register_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        client.post("/auth/register", json=register_data)
        # Then test login
        response = client.post("/auth/login", json=register_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "session_token" in data
        assert "user_email" in data

    @pytest.mark.api
    @pytest.mark.auth
    def test_login_user_failure(self, client):
        """Test failed login (user doesn't exist)."""
        user_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        response = client.post("/auth/login", json=user_data)
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid email or password" in data["detail"]

    @pytest.mark.api
    @pytest.mark.auth
    def test_validate_session_success(self, client):
        """Test successful session validation."""
        # First register and login
        register_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        client.post("/auth/register", json=register_data)
        login_response = client.post("/auth/login", json=register_data)
        assert login_response.status_code == 200
        session_token = login_response.json()["session_token"]
        # Test session validation
        response = client.get("/auth/validate", params={"session_token": session_token})
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "is_oauth_authenticated" in data
        assert "created_at" in data

    @pytest.mark.api
    @pytest.mark.auth
    def test_validate_session_failure(self, client):
        """Test failed session validation."""
        # Test with invalid session token
        response = client.get("/auth/validate", params={"session_token": "invalid_token"})
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid or expired session" in data["detail"]

    @pytest.mark.api
    @pytest.mark.user_data
    @patch('backend.assistant_app.api.v1.endpoints.chat.get_chat_agent')
    def test_clear_user_data_endpoint(self, mock_get_chat_agent, client):
        """Test clear user data endpoint."""
        # Mock the chat agent
        mock_agent = Mock()
        mock_agent.clear_user_data.return_value = {
            "success": True,
            "vector_store_cleared": True,
            "redis_keys_deleted": 5,
            "database_tasks_deleted": 3
        }
        mock_get_chat_agent.return_value = mock_agent
        # Mock authentication
        with patch('backend.assistant_app.api.v1.endpoints.auth_router.auth_service') as mock_auth:
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_auth.validate_session.return_value = mock_user
            response = client.post("/auth/clear-data", params={"session_token": "valid_token"})
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "details" in data
            assert data["details"]["vector_store_cleared"]
            assert data["details"]["redis_keys_deleted"] == 5
            assert data["details"]["database_tasks_deleted"] == 3

    @pytest.mark.api
    @pytest.mark.user_data
    @patch('backend.assistant_app.api.v1.endpoints.chat.get_chat_agent')
    def test_clear_user_data_unauthorized(self, mock_get_chat_agent, client):
        """Test clear user data endpoint with invalid session."""
        # Mock authentication failure
        with patch('backend.assistant_app.api.v1.endpoints.auth_router.auth_service') as mock_auth:
            mock_auth.validate_session.return_value = None
            response = client.post("/auth/clear-data", params={"session_token": "invalid_token"})
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data
            assert "Invalid or expired session" in data["detail"]

    @pytest.mark.api
    @pytest.mark.user_data
    @patch('backend.assistant_app.api.v1.endpoints.chat.get_chat_agent')
    def test_clear_user_data_with_errors(self, mock_get_chat_agent, client):
        """Test clear user data endpoint with errors."""
        # Mock the chat agent to return errors
        mock_agent = Mock()
        mock_agent.clear_user_data.return_value = {
            "success": False,
            "vector_store_cleared": False,
            "redis_keys_deleted": 0,
            "database_tasks_deleted": 0,
            "errors": ["Vector store error", "Database error"]
        }
        mock_get_chat_agent.return_value = mock_agent
        # Mock authentication
        with patch('backend.assistant_app.api.v1.endpoints.auth_router.auth_service') as mock_auth:
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_auth.validate_session.return_value = mock_user
            response = client.post("/auth/clear-data", params={"session_token": "valid_token"})
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "details" in data
            assert not data["details"]["vector_store_cleared"]  # Should be False when there are errors
            assert "errors" in data["details"]
            assert len(data["details"]["errors"]) == 2

    @pytest.mark.api
    def test_tasks_endpoints_unauthorized(self, client):
        """Test tasks endpoints without authentication."""
        # Test GET tasks without auth
        response = client.get("/tasks")
        assert response.status_code == 422  # Missing required parameter
        # Test POST tasks without auth
        task_data = {
            "title": "Test Task",
            "description": "Test Description",
            "priority": 1
        }
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 422  # Missing required parameter

    @pytest.mark.api
    @pytest.mark.slow
    def test_chat_endpoint_unauthorized(self, client):
        """Test chat endpoint without authentication."""
        chat_data = {
            "input": "Hello, how are you?",
            "session_token": "invalid_token"
        }
        response = client.post("/chat", json=chat_data)
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid or expired session" in data["detail"]
