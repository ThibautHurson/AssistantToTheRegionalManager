from unittest.mock import Mock, patch, AsyncMock
import pytest
from backend.assistant_app.services.task_detector import TaskDetector


class TestTaskDetector:
    """Test cases for TaskDetector service."""

    @pytest.fixture
    def task_detector(self):
        """Create a TaskDetector instance for testing."""
        with patch.dict('os.environ', {'MISTRAL_KEY': 'test_key'}):
            with patch('backend.assistant_app.services.task_detector.Mistral') as mock_mistral:
                mock_client = Mock()
                mock_chat = Mock()
                mock_chat.complete_async = AsyncMock()
                mock_client.chat = mock_chat
                mock_mistral.return_value = mock_client
                detector = TaskDetector()
                detector.client = mock_client  # Replace with mock
                return detector

    @pytest.fixture
    def sample_task_email(self):
        """Sample email content that contains a task."""
        return {
            'body': ('Please review the quarterly report by Friday. '
                     'This is high priority and needs your attention.'),
            'date': '2024-01-15T10:00:00Z',
            'from': 'boss@company.com',
            'subject': 'Action required: Review quarterly report',
            'to': 'employee@company.com'
        }

    @pytest.fixture
    def sample_email_content(self):
        """Sample email content that doesn't contain a task."""
        return {
            'body': ('Hi team, we need to have a meeting tomorrow at 2pm to discuss '
                     'the project timeline. Please prepare your updates.'),
            'date': '2024-01-15T10:00:00Z',
            'from': 'manager@company.com',
            'subject': 'Meeting tomorrow at 2pm',
            'to': 'team@company.com'
        }

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.services.task_detector.Mistral')
    async def test_is_task_relevant_true(self, mock_mistral, task_detector):
        """Test when email content is relevant."""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"is_relevant": true}'
        task_detector.client.chat.complete_async.return_value = mock_response

        # Test task relevance
        result = await task_detector._is_task_relevant("Please complete this task by Friday")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.services.task_detector.Mistral')
    async def test_is_task_relevant_false(self, mock_mistral, task_detector):
        """Test when email content is not relevant."""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"is_relevant": false}'
        task_detector.client.chat.complete_async.return_value = mock_response

        # Test task relevance
        result = await task_detector._is_task_relevant("Newsletter: Weekly updates")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.services.task_detector.Mistral')
    async def test_extract_task_details_success(self, mock_mistral, task_detector):
        """Test successful task details extraction."""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '''
        {
            "title": "Review quarterly report",
            "description": "Review the quarterly report by Friday",
            "due_date": "2024-01-19",
            "priority": 0
        }
        '''
        task_detector.client.chat.complete_async.return_value = mock_response

        # Test task extraction
        result = await task_detector._extract_task_details(
            "Please review the quarterly report by Friday")
        assert result["title"] == "Review quarterly report"
        assert result["description"] == "Review the quarterly report by Friday"
        assert result["due_date"] == "2024-01-19"
        assert result["priority"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.services.task_detector.Mistral')
    async def test_extract_task_details_invalid_json(self, mock_mistral, task_detector):
        """Test task extraction with invalid JSON response."""
        # Mock the LLM response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'Invalid JSON response'
        task_detector.client.chat.complete_async.return_value = mock_response

        # Test task extraction
        result = await task_detector._extract_task_details(
            "Please review the quarterly report by Friday")
        assert result["title"] == "Task from email"
        assert result["description"].startswith(
            "Please review the quarterly report by Friday")
        assert result["priority"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.services.task_detector.Mistral')
    async def test_process_email_with_task(self, mock_mistral, task_detector, sample_task_email):
        """Test processing email that contains a task."""
        # Mock the LLM responses
        mock_response_relevant = Mock()
        mock_response_relevant.choices = [Mock()]
        mock_response_relevant.choices[0].message = Mock()
        mock_response_relevant.choices[0].message.content = '{"is_relevant": true}'

        mock_response_details = Mock()
        mock_response_details.choices = [Mock()]
        mock_response_details.choices[0].message = Mock()
        mock_response_details.choices[0].message.content = '''
        {
            "title": "Review quarterly report",
            "description": "Review the quarterly report by Friday",
            "due_date": "2024-01-19",
            "priority": 0
        }
        '''

        task_detector.client.chat.complete_async.side_effect = [
                mock_response_relevant,
                mock_response_details
        ]

        # Test email processing
        result = await task_detector.process_email(
            sample_task_email['body'],
            sample_task_email['subject']
        )
        assert result is not None
        assert result["title"] == "Review quarterly report"
        assert result["priority"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.services.task_detector.Mistral')
    async def test_process_email_no_task(self, mock_mistral, task_detector, sample_email_content):
        """Test processing email that doesn't contain a task."""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"is_relevant": false}'
        task_detector.client.chat.complete_async.return_value = mock_response

        # Test email processing
        result = await task_detector.process_email(
            sample_email_content['body'],
            sample_email_content['subject']
        )
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('backend.assistant_app.services.task_detector.Mistral')
    async def test_process_email_api_error(self, mock_mistral, task_detector, sample_task_email):
        """Test processing email when API call fails."""
        # Mock LLM to raise exception
        task_detector.client.chat.complete_async.side_effect = Exception("API Error")

        # Test email processing
        result = await task_detector.process_email(
            sample_task_email['body'],
            sample_task_email['subject']
        )
        assert result is None

    @pytest.mark.unit
    def test_init_without_api_key(self):
        """Test TaskDetector initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="MISTRAL_KEY environment variable is not set"):
                TaskDetector()

    @pytest.mark.unit
    def test_init_with_api_key(self):
        """Test TaskDetector initialization with API key."""
        with patch.dict('os.environ', {'MISTRAL_KEY': 'test_key'}):
            detector = TaskDetector()
            assert detector.model == "mistral-small-latest"
            assert detector.client is not None
