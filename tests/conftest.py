"""Pytest configuration and fixtures."""

import os
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / ".." / "backend"))

# Set test environment variables before importing app
os.environ.setdefault("AZURE_CLIENT_ID", "test-client-id")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("AZURE_TENANT_ID", "common")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "test-api-hash")
os.environ.setdefault("TELEGRAM_PHONE", "+1234567890")
os.environ.setdefault("GITHUB_TOKEN", "ghp_test-github-token")
os.environ.setdefault("GITHUB_USERNAME", "testuser")


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application for testing."""
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_session_id() -> str:
    """Return a mock session ID."""
    return "test-session-id-12345"


@pytest.fixture
def mock_access_token() -> str:
    """Return a mock access token."""
    return "test-access-token-67890"


@pytest.fixture
def authenticated_client(client: TestClient, mock_session_id: str) -> TestClient:
    """Create an authenticated test client with session cookie."""
    client.cookies.set("session_id", mock_session_id)
    return client


@pytest.fixture
def mock_graph_client() -> MagicMock:
    """Create a mock GraphClient."""
    mock = MagicMock()
    mock.get_me = AsyncMock(
        return_value={
            "displayName": "Test User",
            "mail": "test@example.com",
            "id": "user-123",
        }
    )
    mock.list_folder = AsyncMock(
        return_value={
            "value": [
                {"id": "folder-1", "name": "Diary", "folder": {}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-15T10:00:00Z"},
                {"id": "folder-2", "name": "Projects", "folder": {}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-15T10:00:00Z"},
                {"id": "folder-3", "name": "Study", "folder": {}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-15T10:00:00Z"},
                {"id": "folder-4", "name": "Inbox", "folder": {}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-15T10:00:00Z"},
            ]
        }
    )
    mock.get_file_content = AsyncMock(return_value=b"# Test Note\n\nThis is a test.")
    mock.get_item_by_path = AsyncMock(return_value={
        "id": "item-123",
        "name": "test.md",
        "createdDateTime": "2024-01-15T08:00:00Z",
        "lastModifiedDateTime": "2024-01-15T10:00:00Z",
    })
    mock.upload_file = AsyncMock(return_value={"id": "file-123", "name": "test.md"})
    mock.create_folder = AsyncMock(return_value={"id": "folder-123", "name": "NewFolder"})
    mock.delete_item = AsyncMock(return_value={"success": True})
    mock.list_task_lists = AsyncMock(
        return_value={
            "value": [
                {"id": "list-1", "displayName": "Tasks"},
                {"id": "list-2", "displayName": "Work"},
            ]
        }
    )
    mock.list_tasks = AsyncMock(
        return_value={
            "value": [
                {
                    "id": "task-1",
                    "title": "Test Task",
                    "status": "notStarted",
                    "importance": "normal",
                }
            ]
        }
    )
    mock.create_task = AsyncMock(return_value={"id": "task-new", "title": "New Task"})
    mock.complete_task = AsyncMock(return_value={"id": "task-1", "status": "completed"})
    mock.delete_task = AsyncMock(return_value={"success": True})
    mock.get_calendar_view = AsyncMock(
        return_value={
            "value": [
                {
                    "id": "event-1",
                    "subject": "Test Meeting",
                    "start": {"dateTime": "2024-01-15T10:00:00"},
                    "end": {"dateTime": "2024-01-15T11:00:00"},
                    "location": {"displayName": "Room 1"},
                    "organizer": {"emailAddress": {"name": "Organizer", "address": "org@test.com"}},
                }
            ]
        }
    )
    mock.create_event = AsyncMock(return_value={"id": "event-new", "subject": "New Event"})
    mock.delete_event = AsyncMock(return_value={"success": True})
    mock.list_messages = AsyncMock(
        return_value={
            "value": [
                {
                    "id": "msg-1",
                    "subject": "Test Email",
                    "from": {"emailAddress": {"name": "Sender", "address": "sender@test.com"}},
                    "receivedDateTime": "2024-01-15T09:00:00Z",
                    "isRead": False,
                    "bodyPreview": "This is a test email preview.",
                }
            ]
        }
    )
    mock.get_message = AsyncMock(
        return_value={
            "id": "msg-1",
            "subject": "Test Email",
            "from": {"emailAddress": {"name": "Sender", "address": "sender@test.com"}},
            "toRecipients": [{"emailAddress": {"address": "test@example.com"}}],
            "receivedDateTime": "2024-01-15T09:00:00Z",
            "isRead": False,
            "body": {"content": "Full email body", "contentType": "text"},
            "hasAttachments": False,
        }
    )
    mock.search_messages = AsyncMock(return_value={"value": []})
    # OneNote mocks
    mock.list_notebooks = AsyncMock(
        return_value={
            "value": [
                {
                    "id": "notebook-1",
                    "displayName": "PersonalAI",
                    "createdDateTime": "2024-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2024-01-15T10:00:00Z",
                }
            ]
        }
    )
    mock.create_notebook = AsyncMock(
        return_value={"id": "notebook-new", "displayName": "New Notebook"}
    )
    mock.list_sections = AsyncMock(
        return_value={
            "value": [
                {
                    "id": "section-1",
                    "displayName": "Diary",
                    "createdDateTime": "2024-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2024-01-15T10:00:00Z",
                }
            ]
        }
    )
    mock.create_section = AsyncMock(
        return_value={"id": "section-new", "displayName": "New Section"}
    )
    mock.list_pages = AsyncMock(
        return_value={
            "value": [
                {
                    "id": "page-1",
                    "title": "2024-01-15",
                    "createdDateTime": "2024-01-15T08:00:00Z",
                    "lastModifiedDateTime": "2024-01-15T10:00:00Z",
                    "parentSection": {"displayName": "Diary"},
                }
            ]
        }
    )
    mock.get_page = AsyncMock(
        return_value={
            "id": "page-1",
            "title": "Test Page",
            "createdDateTime": "2024-01-15T08:00:00Z",
            "lastModifiedDateTime": "2024-01-15T10:00:00Z",
        }
    )
    mock.get_page_content = AsyncMock(
        return_value="<html><body><h1>Test</h1><p>Content here.</p></body></html>"
    )
    mock.create_page = AsyncMock(return_value={"id": "page-new", "title": "New Page"})
    mock.update_page = AsyncMock(return_value={"success": True})
    mock.delete_page = AsyncMock(return_value={"success": True})
    return mock


@pytest.fixture
def mock_get_access_token(mock_access_token: str):
    """Patch get_access_token and get_access_token_for_service at all router locations."""
    # Need to patch at each router's import location, not at auth module
    patches = [
        # get_access_token imports
        patch("routers.actions.get_access_token", return_value=mock_access_token),
        patch("routers.chat.get_access_token", return_value=mock_access_token),
        patch("routers.email.get_access_token", return_value=mock_access_token),
        patch("routers.sync.get_access_token", return_value=mock_access_token),
        # get_access_token_for_service imports
        patch("routers.calendar.get_access_token_for_service", return_value=mock_access_token),
        patch("routers.notes.get_access_token_for_service", return_value=mock_access_token),
        patch("routers.onenote.get_access_token_for_service", return_value=mock_access_token),
        patch("routers.tasks.get_access_token_for_service", return_value=mock_access_token),
    ]

    for p in patches:
        p.start()

    yield mock_access_token

    for p in patches:
        p.stop()


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Create a mock vector store."""
    mock = MagicMock()
    mock.similarity_search_with_score = MagicMock(return_value=[])
    mock.add_documents = MagicMock()
    mock.delete = MagicMock()
    mock.get = MagicMock(return_value={"ids": []})
    mock._collection = MagicMock()
    mock._collection.count = MagicMock(return_value=10)
    return mock


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock LLM."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="Test AI response"))
    mock.astream = AsyncMock()
    return mock


@pytest.fixture
def sample_note_content() -> str:
    """Return sample note content."""
    return """# Daily Diary

## What I did today
- Worked on project
- Had a meeting

## Notes
Some important notes here.
"""


@pytest.fixture
def sample_task_data() -> dict[str, Any]:
    """Return sample task data."""
    return {
        "title": "Test Task",
        "body": "Task description",
        "due_date": "2024-01-20T00:00:00Z",
        "list_id": "list-1",
        "importance": "high",
    }


@pytest.fixture
def sample_event_data() -> dict[str, Any]:
    """Return sample event data."""
    return {
        "subject": "Test Event",
        "start_datetime": "2024-01-20T10:00:00Z",
        "end_datetime": "2024-01-20T11:00:00Z",
        "body": "Event description",
        "location": "Conference Room",
        "attendees": ["attendee@example.com"],
    }


@pytest.fixture
def sample_email_data() -> dict[str, Any]:
    """Return sample email data."""
    return {
        "to": ["recipient@example.com"],
        "subject": "Test Email",
        "body": "This is the email body.",
        "reply_to_id": None,
    }
