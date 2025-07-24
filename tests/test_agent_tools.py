from unittest.mock import Mock, patch
from datetime import datetime
import json
import pytest
from backend.assistant_app.agents.tools.agent_task_tools import (
    add_task, delete_task, update_task, list_tasks, get_next_task
)
from backend.assistant_app.agents.tools.calendar_tools import (
    list_calendar_events, create_calendar_event, delete_calendar_event
)
from backend.assistant_app.agents.tools.gmail_tools import (
    search_gmail, send_gmail
)


class TestAgentTaskTools:
    """Test cases for agent task tools functions."""

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            "title": "Test Task",
            "description": "Test task description",
            "priority": 2,
            "due_date": datetime(2024, 1, 20),
            "status": "pending"
        }

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_add_task_success(self, mock_task_manager_class, sample_task_data):
        """Test successful task creation."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager

        # Mock task object
        mock_task = Mock()
        mock_task.title = sample_task_data["title"]
        mock_task.id = "task123"
        mock_task_manager.add_task.return_value = mock_task

        result = add_task(
            user_email="test@example.com",
            title=sample_task_data["title"],
            description=sample_task_data["description"],
            due_date=sample_task_data["due_date"],
            priority=sample_task_data["priority"]
        )

        assert "Task 'Test Task' added successfully" in result
        assert "task123" in result
        mock_task_manager.add_task.assert_called_once()

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_delete_task_success(self, mock_task_manager_class):
        """Test successful task deletion."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager
        mock_task_manager.delete_task.return_value = True

        result = delete_task(
            user_email="test@example.com",
            task_id="task123"
        )

        assert "Task task123 deleted successfully" in result
        mock_task_manager.delete_task.assert_called_once_with("task123")

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_delete_task_not_found(self, mock_task_manager_class):
        """Test task deletion when task not found."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager
        mock_task_manager.delete_task.return_value = False

        result = delete_task(
            user_email="test@example.com",
            task_id="task123"
        )

        assert "Task task123 not found" in result

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_update_task_success(self, mock_task_manager_class):
        """Test successful task update."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager

        # Mock updated task
        mock_task = Mock()
        mock_task.title = "Updated Task"
        mock_task_manager.update_task.return_value = mock_task

        result = update_task(
            user_email="test@example.com",
            task_id="task123",
            title="Updated Task",
            priority=1
        )

        assert "Task 'Updated Task' updated successfully" in result
        mock_task_manager.update_task.assert_called_once_with(
            "task123", title="Updated Task", priority=1)

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_update_task_not_found(self, mock_task_manager_class):
        """Test task update when task not found."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager
        mock_task_manager.update_task.return_value = None

        result = update_task(
            user_email="test@example.com",
            task_id="task123",
            title="Updated Task"
        )

        assert "Task task123 not found" in result

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_list_tasks_with_results(self, mock_task_manager_class):
        """Test listing tasks with results."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager

        # Mock tasks
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.title = "Task 1"
        mock_task1.description = "Description 1"
        mock_task1.due_date = datetime(2024, 1, 20)
        mock_task1.priority = 1
        mock_task1.status = "pending"

        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.title = "Task 2"
        mock_task2.description = None
        mock_task2.due_date = None
        mock_task2.priority = 2
        mock_task2.status = "completed"

        mock_task_manager.get_tasks.return_value = [mock_task1, mock_task2]

        result = list_tasks(user_email="test@example.com")

        assert "Tasks:" in result
        assert "Task 1 (ID: task1)" in result
        assert "Task 2 (ID: task2)" in result
        assert "Description: Description 1" in result
        assert "Due: 2024-01-20" in result

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_list_tasks_no_results(self, mock_task_manager_class):
        """Test listing tasks with no results."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager
        mock_task_manager.get_tasks.return_value = []

        result = list_tasks(user_email="test@example.com")

        assert result == "No tasks found"

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_get_next_task_with_task(self, mock_task_manager_class):
        """Test getting next task when one exists."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager

        # Mock next task
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.title = "Next Task"
        mock_task.description = "Next task description"
        mock_task.due_date = datetime(2024, 1, 20)
        mock_task.priority = 1
        mock_task.status = "pending"

        mock_task_manager.get_next_task.return_value = mock_task

        result = get_next_task(user_email="test@example.com")

        assert "Next task: Next Task (ID: task123)" in result
        assert "Description: Next task description" in result
        assert "Due: 2024-01-20" in result
        assert "Priority: 1" in result
        assert "Status: pending" in result

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.agent_task_tools.TaskManager')
    def test_get_next_task_no_task(self, mock_task_manager_class):
        """Test getting next task when none exists."""
        # Mock task manager instance
        mock_task_manager = Mock()
        mock_task_manager_class.return_value = mock_task_manager
        mock_task_manager.get_next_task.return_value = None

        result = get_next_task(user_email="test@example.com")

        assert result == "No pending tasks found"


class TestCalendarTools:
    """Test cases for calendar tools functions."""

    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            "summary": "Team Meeting",
            "description": "Weekly team sync",
            "start_time": "2024-01-20T10:00:00Z",
            "end_time": "2024-01-20T11:00:00Z",
            "attendees": ["team@company.com"]
        }

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.calendar_tools.load_credentials')
    @patch('backend.assistant_app.agents.tools.calendar_tools.build')
    def test_list_calendar_events_success(self, mock_build, mock_load_credentials):
        """Test successful event listing."""
        # Mock credentials
        mock_creds = Mock()
        mock_load_credentials.return_value = mock_creds

        # Mock calendar service
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock events response
        mock_events = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Meeting 1",
                    "start": {"dateTime": "2024-01-20T10:00:00Z"},
                    "end": {"dateTime": "2024-01-20T11:00:00Z"},
                    "description": "Test meeting",
                    "location": "Conference Room",
                    "attendees": [{"email": "attendee@example.com"}],
                    "htmlLink": "https://calendar.google.com/event1",
                    "status": "confirmed"
                }
            ]
        }
        mock_service.events.return_value.list.return_value.execute.\
            return_value = mock_events

        result = list_calendar_events(
            user_email="test@example.com",
            max_results=10
        )

        # Parse JSON result
        result_data = json.loads(result)

        assert result_data["message"] == "Found 1 events"
        assert len(result_data["events"]) == 1
        assert result_data["events"][0]["summary"] == "Meeting 1"

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.calendar_tools.load_credentials')
    def test_list_calendar_events_no_credentials(self, mock_load_credentials):
        """Test event listing when no credentials are available."""
        # Mock no credentials
        mock_load_credentials.return_value = None

        result = list_calendar_events(user_email="test@example.com")

        # Parse JSON result
        result_data = json.loads(result)

        assert "error" in result_data
        assert "No valid credentials found" in result_data["error"]

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.calendar_tools.load_credentials')
    @patch('backend.assistant_app.agents.tools.calendar_tools.build')
    def test_create_calendar_event_success(self, mock_build, mock_load_credentials,
                                           sample_event_data):
        """Test successful event creation."""
        # Mock credentials
        mock_creds = Mock()
        mock_load_credentials.return_value = mock_creds

        # Mock calendar service
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock event creation response
        mock_event = {
            "id": "event123",
            "summary": "Team Meeting",
            "start": {"dateTime": "2024-01-20T10:00:00Z"},
            "end": {"dateTime": "2024-01-20T11:00:00Z"},
            "description": "Weekly team sync",
            "location": "",
            "htmlLink": "https://calendar.google.com/event123",
            "attendees": [{"email": "team@company.com"}]
        }
        mock_service.events.return_value.insert.return_value.execute.return_value = mock_event

        result = create_calendar_event(
            user_email="test@example.com",
            summary=sample_event_data["summary"],
            start_time=sample_event_data["start_time"],
            end_time=sample_event_data["end_time"],
            description=sample_event_data["description"],
            attendees=sample_event_data["attendees"]
        )

        # Parse JSON result
        result_data = json.loads(result)

        assert result_data["message"] == "Event created successfully"
        assert result_data["event"]["id"] == "event123"
        assert result_data["event"]["summary"] == "Team Meeting"

    @pytest.mark.unit
    @patch('backend.assistant_app.agents.tools.calendar_tools.load_credentials')
    @patch('backend.assistant_app.agents.tools.calendar_tools.build')
    def test_delete_calendar_event_success(self, mock_build, mock_load_credentials):
        """Test successful event deletion."""
        # Mock credentials
        mock_creds = Mock()
        mock_load_credentials.return_value = mock_creds

        # Mock calendar service
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock successful deletion
        mock_service.events.return_value.delete.return_value.execute.return_value = {}

        result = delete_calendar_event(
            user_email="test@example.com",
            event_id="event123"
        )

        # Parse JSON result
        result_data = json.loads(result)

        assert result_data["message"] == "Event deleted successfully"
        assert result_data["event_id"] == "event123"


class TestGmailTools:
    """Test cases for Gmail tools functions."""

    @pytest.fixture
    def sample_email_data(self):
        """Sample email data for testing."""
        return {
            "to": "recipient@example.com",
            "subject": "Test Email",
            "body": "This is a test email body.",
            "cc": ["cc@example.com"],
            "bcc": ["bcc@example.com"]
        }

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.tools.gmail_tools.load_credentials')
    @patch('backend.assistant_app.agents.tools.gmail_tools.build')
    @patch('backend.assistant_app.agents.tools.gmail_tools.get_gmail')
    async def test_search_gmail_success(self, mock_get_gmail, mock_build, mock_load_credentials):
        """Test successful email search."""
        # Mock credentials
        mock_creds = Mock()
        mock_load_credentials.return_value = mock_creds

        # Mock Gmail service
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock search response
        mock_messages = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"}
            ]
        }
        mock_service.users.return_value.messages.return_value.list.return_value.execute.\
            return_value = mock_messages

        # Mock get_gmail to return content
        mock_get_gmail.return_value = ("Test email content", "history123", ["INBOX"])

        result = await search_gmail("test query", "test@example.com")

        # Parse JSON result
        result_data = json.loads(result)

        assert len(result_data) > 0
        assert "content" in result_data[0]
        assert "message_id" in result_data[0]
        assert result_data[0]["content"] == "Test email content"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.agents.tools.gmail_tools.load_credentials')
    @patch('backend.assistant_app.agents.tools.gmail_tools.build')
    async def test_send_gmail_success(self, mock_build, mock_load_credentials, sample_email_data):
        """Test successful email sending."""
        # Mock credentials
        mock_creds = Mock()
        mock_load_credentials.return_value = mock_creds

        # Mock Gmail service
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock message creation and sending
        mock_message = {"id": "msg123", "threadId": "thread123"}
        mock_service.users.return_value.messages.return_value.send.return_value.execute.\
            return_value = mock_message

        result = await send_gmail(
            to=sample_email_data["to"],
            subject=sample_email_data["subject"],
            body=sample_email_data["body"],
            user_email="test@example.com"
        )

        # Expect a string response, not JSON
        assert "Email sent to recipient@example.com" in result
        assert "Test Email" in result
        assert "msg123" in result
