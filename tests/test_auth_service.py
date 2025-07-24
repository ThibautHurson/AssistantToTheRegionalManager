from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pytest
from backend.assistant_app.services.auth_service import AuthService



class TestAuthService:
    """Test cases for AuthService."""

    @pytest.fixture
    def auth_service(self):
        """Create an AuthService instance for testing."""
        return AuthService()

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "email": "test@example.com",
            "password": "testpassword123"
        }

    @pytest.mark.unit
    def test_hash_password(self, auth_service):
        """Test password hashing functionality."""
        password = "testpassword123"
        hashed = auth_service.hash_password(password)

        # Verify the hash is different from original
        assert hashed != password
        # Verify it's a string
        assert isinstance(hashed, str)
        # Verify it's a valid bcrypt hash
        assert hashed.startswith('$2b$')

    @pytest.mark.unit
    def test_verify_password_success(self, auth_service):
        """Test successful password verification."""
        password = "testpassword123"
        hashed = auth_service.hash_password(password)

        result = auth_service.verify_password(password, hashed)
        assert result is True

    @pytest.mark.unit
    def test_verify_password_failure(self, auth_service):
        """Test failed password verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = auth_service.hash_password(password)

        result = auth_service.verify_password(wrong_password, hashed)
        assert result is False

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_register_user_success(self, mock_get_db, auth_service, sample_user_data):
        """Test successful user registration."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Mock that user doesn't exist
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock user creation
        mock_user = Mock()
        mock_user.id = "user123"
        mock_session.add.return_value = None
        mock_session.refresh.return_value = None

        result = auth_service.register_user(
            sample_user_data["email"],
            sample_user_data["password"]
        )

        assert result[0] is True  # success boolean
        assert "successfully" in result[1]  # message

        # Verify user was added to database
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_register_user_already_exists(self, mock_get_db, auth_service, sample_user_data):
        """Test user registration when user already exists."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Mock that user already exists
        existing_user = Mock()
        existing_user.email = sample_user_data["email"]
        mock_session.query.return_value.filter.return_value.first.return_value = existing_user

        result = auth_service.register_user(
            sample_user_data["email"],
            sample_user_data["password"]
        )

        assert result[0] is False  # success boolean
        assert "already exists" in result[1].lower()  # message

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_login_user_success(self, mock_get_db, auth_service, sample_user_data):
        """Test successful user login."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Create a mock user with hashed password
        mock_user = Mock()
        mock_user.email = sample_user_data["email"]
        mock_user.password_hash = auth_service.hash_password(sample_user_data["password"])
        mock_user.id = "user123"

        # Mock that user exists
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user

        result = auth_service.login_user(
            sample_user_data["email"],
            sample_user_data["password"]
        )

        assert result[0] is not None  # session token
        assert "successful" in result[1]  # message

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_login_user_invalid_credentials(self, mock_get_db, auth_service, sample_user_data):
        """Test login with invalid credentials."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Mock that user doesn't exist
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.login_user(
            sample_user_data["email"],
            sample_user_data["password"]
        )

        assert result[0] is None  # no session token
        assert "Invalid email or password" in result[1]

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_validate_session_success(self, mock_get_db, auth_service):
        """Test successful session validation."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Create a mock session
        mock_session_obj = Mock()
        mock_session_obj.user = Mock()
        mock_session_obj.user.email = "test@example.com"
        mock_session_obj.user.id = "user123"
        mock_session_obj.is_active = True
        mock_session_obj.expires_at = datetime.utcnow() + timedelta(hours=1)

        # Mock that session exists and is valid
        mock_session.query.return_value.filter.return_value.first.return_value = mock_session_obj

        result = auth_service.validate_session("valid_session_token")

        assert result is not None
        assert result.email == "test@example.com"

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_validate_session_invalid_token(self, mock_get_db, auth_service):
        """Test session validation with invalid token."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Mock that session doesn't exist
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.validate_session("invalid_session_token")

        assert result is None

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_validate_session_expired(self, mock_get_db, auth_service):
        """Test session validation with expired session."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Mock that session doesn't exist (expired sessions are filtered out)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.validate_session("expired_session_token")

        assert result is None

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    @patch('backend.assistant_app.services.auth_service.auth_logger')
    def test_logout_user_success(self, mock_auth_logger, mock_get_db, auth_service):
        """Test successful user logout."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Create a mock session
        mock_session_obj = Mock()
        mock_session_obj.is_active = True
        mock_session_obj.user = Mock()
        mock_session_obj.user.email = "test@example.com"

        # Mock that session exists
        mock_session.query.return_value.filter.return_value.first.return_value = mock_session_obj

        result = auth_service.logout_user("valid_session_token")

        assert result is True
        # Verify session was deactivated
        assert mock_session_obj.is_active is False
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_logout_user_invalid_token(self, mock_get_db, auth_service):
        """Test logout with invalid session token."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Mock that session doesn't exist
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.logout_user("invalid_session_token")

        assert result is False

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    @patch('backend.assistant_app.services.auth_service.auth_logger')
    def test_update_oauth_status(self, mock_auth_logger, mock_get_db, auth_service):
        """Test updating user OAuth status."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = iter([mock_session])

        # Create a mock user
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.email = "test@example.com"
        mock_user.is_oauth_authenticated = False

        # Mock that user exists
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user

        result = auth_service.update_oauth_status("user123", True)

        assert result is True
        # Verify OAuth status was updated
        assert mock_user.is_oauth_authenticated is True
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @patch('backend.assistant_app.services.auth_service.get_db')
    def test_get_user_session_info(self, mock_get_db, auth_service):
        """Test getting user session info."""
        # Mock database session for validate_session call
        mock_session1 = Mock()
        mock_session_obj = Mock()
        mock_session_obj.user = Mock()
        mock_session_obj.user.email = "test@example.com"
        mock_session_obj.is_active = True
        mock_session_obj.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_session1.query.return_value.filter.return_value.first.return_value = mock_session_obj

        # Mock database session for get_user_session_info call
        mock_session2 = Mock()
        mock_session2.query.return_value.filter.return_value.first.return_value = mock_session_obj

        # Mock get_db to return different sessions for different calls
        mock_get_db.side_effect = [iter([mock_session1]), iter([mock_session2])]

        result = auth_service.get_user_session_info("token123")

        assert result is not None
        assert result["session_token"] == "token123"
        assert result["email"] == "test@example.com"
        assert result["user_id"] is not None
