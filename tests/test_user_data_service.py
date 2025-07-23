from unittest.mock import Mock, patch
import pytest
from backend.assistant_app.services.user_data_service import UserDataService


class TestUserDataService:
    """Test cases for UserDataService."""

    @pytest.mark.unit
    def test_user_data_service_initialization(self):
        """Test UserDataService initialization."""
        service = UserDataService()
        assert service is not None

    @pytest.mark.unit
    @patch('backend.assistant_app.services.user_data_service.HybridContextManager')
    @patch('backend.assistant_app.services.user_data_service.TaskManager')
    def test_clear_user_data_success(self,
                                     mock_task_manager,
                                     mock_context_manager,
                                     sample_user_email):
        """Test successful user data deletion."""
        # Setup mocks
        mock_context_instance = Mock()
        mock_context_instance.clear_user_data.return_value = {
            "vector_store_cleared": True,
            "redis_keys_deleted": 5
        }
        mock_context_manager.return_value = mock_context_instance
        mock_task_instance = Mock()
        mock_task_instance.get_tasks.return_value = [
            Mock(id="task_1"),
            Mock(id="task_2")
        ]
        mock_task_instance.delete_task.return_value = True
        mock_task_manager.return_value = mock_task_instance
        # Execute
        service = UserDataService()
        result = service.clear_user_data(sample_user_email)
        # Assert
        assert result["success"] is True
        assert result["user_id"] == sample_user_email
        assert result["vector_store_cleared"] is True
        assert result["redis_keys_deleted"] == 5
        assert result["database_tasks_deleted"] == 2
        assert len(result["errors"]) == 0
        # Verify calls
        mock_context_manager.assert_called_once()
        mock_task_manager.assert_called_once_with(sample_user_email)
        mock_task_instance.get_tasks.assert_called_once()
        assert mock_task_instance.delete_task.call_count == 2

    @pytest.mark.unit
    @patch('backend.assistant_app.services.user_data_service.HybridContextManager')
    @patch('backend.assistant_app.services.user_data_service.TaskManager')
    def test_clear_user_data_with_errors(self,
                                         mock_task_manager,
                                         mock_context_manager,
                                         sample_user_email):
        """Test user data deletion with errors."""
        # Setup mocks to raise exceptions
        mock_context_manager.side_effect = Exception("Vector store error")
        mock_task_instance = Mock()
        mock_task_instance.get_tasks.side_effect = Exception("Database error")
        mock_task_manager.return_value = mock_task_instance
        # Execute
        service = UserDataService()
        result = service.clear_user_data(sample_user_email)
        # Assert
        assert result["success"] is False
        assert result["user_id"] == sample_user_email
        assert result["vector_store_cleared"] is False
        assert result["redis_keys_deleted"] == 0
        assert result["database_tasks_deleted"] == 0
        assert len(result["errors"]) == 2
        assert "Vector store error" in str(result["errors"][0])
        assert "Database error" in str(result["errors"][1])

    @pytest.mark.unit
    @patch('backend.assistant_app.services.user_data_service.HybridContextManager')
    @patch('backend.assistant_app.services.user_data_service.TaskManager')
    def test_clear_user_data_partial_success(self,
                                             mock_task_manager,
                                             mock_context_manager,
                                             sample_user_email):
        """Test user data deletion with partial success."""
        # Setup mocks - context manager succeeds, task manager fails
        mock_context_instance = Mock()
        mock_context_instance.clear_user_data.return_value = {
            "vector_store_cleared": True,
            "redis_keys_deleted": 3
        }
        mock_context_manager.return_value = mock_context_instance
        mock_task_instance = Mock()
        mock_task_instance.get_tasks.side_effect = Exception(
            "Database connection failed"
        )
        mock_task_manager.return_value = mock_task_instance
        # Execute
        service = UserDataService()
        result = service.clear_user_data(sample_user_email)
        # Assert
        assert result["success"] is False  # Should be False due to task deletion error
        assert result["user_id"] == sample_user_email
        assert result["vector_store_cleared"] is True
        assert result["redis_keys_deleted"] == 3
        assert result["database_tasks_deleted"] == 0
        assert len(result["errors"]) == 1
        assert "Database connection failed" in str(result["errors"][0])

    @pytest.mark.unit
    @patch('backend.assistant_app.services.user_data_service.HybridContextManager')
    @patch('backend.assistant_app.services.user_data_service.TaskManager')
    def test_clear_user_data_no_tasks(self,
                                      mock_task_manager,
                                      mock_context_manager,
                                      sample_user_email):
        """Test user data deletion when user has no tasks."""
        # Setup mocks
        mock_context_instance = Mock()
        mock_context_instance.clear_user_data.return_value = {
            "vector_store_cleared": True,
            "redis_keys_deleted": 0
        }
        mock_context_manager.return_value = mock_context_instance
        mock_task_instance = Mock()
        mock_task_instance.get_tasks.return_value = []  # No tasks
        mock_task_manager.return_value = mock_task_instance
        # Execute
        service = UserDataService()
        result = service.clear_user_data(sample_user_email)
        # Assert
        assert result["success"] is True
        assert result["user_id"] == sample_user_email
        assert result["vector_store_cleared"] is True
        assert result["redis_keys_deleted"] == 0
        assert result["database_tasks_deleted"] == 0
        assert len(result["errors"]) == 0

    @pytest.mark.unit
    @patch('backend.assistant_app.services.user_data_service.HybridContextManager')
    @patch('backend.assistant_app.services.user_data_service.TaskManager')
    def test_clear_user_data_task_deletion_failure(self,
                                                   mock_task_manager,
                                                   mock_context_manager,
                                                   sample_user_email):
        """Test user data deletion when some task deletions fail."""
        # Setup mocks
        mock_context_instance = Mock()
        mock_context_instance.clear_user_data.return_value = {
            "vector_store_cleared": True,
            "redis_keys_deleted": 2
        }
        mock_context_manager.return_value = mock_context_instance
        mock_task_instance = Mock()
        mock_task_instance.get_tasks.return_value = [
            Mock(id="task_1"),
            Mock(id="task_2"),
            Mock(id="task_3")
        ]
        # First task deletion succeeds, second fails, third succeeds
        mock_task_instance.delete_task.side_effect = [True, False, True]
        mock_task_manager.return_value = mock_task_instance
        # Execute
        service = UserDataService()
        result = service.clear_user_data(sample_user_email)
        # Assert
        assert result["success"] is True  # Should still be True as vector store cleared
        assert result["user_id"] == sample_user_email
        assert result["vector_store_cleared"] is True
        assert result["redis_keys_deleted"] == 2
        assert result["database_tasks_deleted"] == 2  # Only 2 successful deletions
        assert len(result["errors"]) == 0
        # Verify task deletion was attempted for all tasks
        assert mock_task_instance.delete_task.call_count == 3
