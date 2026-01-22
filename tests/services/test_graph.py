"""Tests for the Microsoft Graph client service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.graph import GraphClient


class TestGraphClientInit:
    """Tests for GraphClient initialization."""

    def test_client_init(self):
        """Test client initialization."""
        client = GraphClient("test-access-token")

        assert client.access_token == "test-access-token"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test-access-token"
        assert client.headers["Content-Type"] == "application/json"


class TestGraphClientRequests:
    """Tests for GraphClient request methods."""

    @pytest.fixture
    def client(self) -> GraphClient:
        """Create a GraphClient instance."""
        return GraphClient("test-token")

    @pytest.mark.asyncio
    async def test_request_get(self, client: GraphClient):
        """Test GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"data": "value"})
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await client._request("GET", "/me")

            assert result == {"data": "value"}
            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_post(self, client: GraphClient):
        """Test POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json = MagicMock(return_value={"id": "new-id"})
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await client._request("POST", "/me/tasks", json={"title": "Task"})

            assert result == {"id": "new-id"}

    @pytest.mark.asyncio
    async def test_request_204_no_content(self, client: GraphClient):
        """Test request with 204 No Content response."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await client._request("DELETE", "/me/events/123")

            assert result == {"success": True}


class TestOneDriveOperations:
    """Tests for OneDrive operations."""

    @pytest.fixture
    def client(self) -> GraphClient:
        """Create a GraphClient instance."""
        return GraphClient("test-token")

    @pytest.mark.asyncio
    async def test_list_drive_root(self, client: GraphClient):
        """Test listing drive root."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"value": [{"name": "folder1"}, {"name": "file1.txt"}]}

            result = await client.list_drive_root()

            mock_request.assert_called_once_with("GET", "/me/drive/root/children")
            assert len(result["value"]) == 2

    @pytest.mark.asyncio
    async def test_list_folder(self, client: GraphClient):
        """Test listing folder contents."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"value": [{"name": "note.md"}]}

            await client.list_folder("PersonalAI/Diary")

            mock_request.assert_called_once_with(
                "GET", "/me/drive/root:/PersonalAI/Diary:/children"
            )

    @pytest.mark.asyncio
    async def test_list_folder_with_spaces(self, client: GraphClient):
        """Test listing folder with spaces in path."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            await client.list_folder("My Documents/Notes")

            mock_request.assert_called_once_with(
                "GET", "/me/drive/root:/My%20Documents/Notes:/children"
            )

    @pytest.mark.asyncio
    async def test_get_file_content(self, client: GraphClient):
        """Test getting file content."""
        with patch.object(client, "_request_content", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = b"# Hello World"

            result = await client.get_file_content("PersonalAI/Diary/note.md")

            assert result == b"# Hello World"

    @pytest.mark.asyncio
    async def test_upload_file(self, client: GraphClient):
        """Test uploading file."""
        with patch.object(client, "_upload_content", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = {"id": "file-id", "name": "note.md"}

            result = await client.upload_file("PersonalAI/note.md", b"content")

            mock_upload.assert_called_once()
            assert result["id"] == "file-id"

    @pytest.mark.asyncio
    async def test_create_folder(self, client: GraphClient):
        """Test creating folder."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "folder-id", "name": "NewFolder"}

            result = await client.create_folder("PersonalAI", "NewFolder")

            assert result["name"] == "NewFolder"

    @pytest.mark.asyncio
    async def test_delete_item(self, client: GraphClient):
        """Test deleting item."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"success": True}

            await client.delete_item("PersonalAI/old-note.md")

            mock_request.assert_called_once_with("DELETE", "/me/drive/root:/PersonalAI/old-note.md")


class TestTaskOperations:
    """Tests for Microsoft To Do operations."""

    @pytest.fixture
    def client(self) -> GraphClient:
        """Create a GraphClient instance."""
        return GraphClient("test-token")

    @pytest.mark.asyncio
    async def test_list_task_lists(self, client: GraphClient):
        """Test listing task lists."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "value": [
                    {"id": "list-1", "displayName": "Tasks"},
                    {"id": "list-2", "displayName": "Work"},
                ]
            }

            result = await client.list_task_lists()

            mock_request.assert_called_once_with("GET", "/me/todo/lists")
            assert len(result["value"]) == 2

    @pytest.mark.asyncio
    async def test_list_tasks(self, client: GraphClient):
        """Test listing tasks."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"value": [{"id": "task-1", "title": "Test"}]}

            await client.list_tasks("list-1")

            mock_request.assert_called_once()
            assert "status ne 'completed'" in str(mock_request.call_args)

    @pytest.mark.asyncio
    async def test_list_tasks_include_completed(self, client: GraphClient):
        """Test listing tasks including completed."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            await client.list_tasks("list-1", include_completed=True)

            # Should not have filter
            call_args = mock_request.call_args
            assert call_args.kwargs.get("params") == {}

    @pytest.mark.asyncio
    async def test_create_task(self, client: GraphClient):
        """Test creating task."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "new-task", "title": "New Task"}

            result = await client.create_task(
                list_id="list-1",
                title="New Task",
                body="Description",
                due_date="2024-01-20T00:00:00Z",
            )

            assert result["title"] == "New Task"
            call_json = mock_request.call_args.kwargs["json"]
            assert call_json["title"] == "New Task"
            assert "body" in call_json
            assert "dueDateTime" in call_json

    @pytest.mark.asyncio
    async def test_complete_task(self, client: GraphClient):
        """Test completing task."""
        with patch.object(client, "update_task", new_callable=AsyncMock) as mock_update:
            await client.complete_task("list-1", "task-1")

            mock_update.assert_called_once_with("list-1", "task-1", {"status": "completed"})

    @pytest.mark.asyncio
    async def test_delete_task(self, client: GraphClient):
        """Test deleting task."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            await client.delete_task("list-1", "task-1")

            mock_request.assert_called_once_with("DELETE", "/me/todo/lists/list-1/tasks/task-1")


class TestCalendarOperations:
    """Tests for calendar operations."""

    @pytest.fixture
    def client(self) -> GraphClient:
        """Create a GraphClient instance."""
        return GraphClient("test-token")

    @pytest.mark.asyncio
    async def test_list_calendars(self, client: GraphClient):
        """Test listing calendars."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"value": [{"id": "cal-1", "name": "Calendar"}]}

            await client.list_calendars()

            mock_request.assert_called_once_with("GET", "/me/calendars")

    @pytest.mark.asyncio
    async def test_get_calendar_view(self, client: GraphClient):
        """Test getting calendar view."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"value": [{"subject": "Meeting"}]}

            await client.get_calendar_view(
                start_datetime="2024-01-15T00:00:00Z",
                end_datetime="2024-01-16T00:00:00Z",
            )

            mock_request.assert_called_once()
            params = mock_request.call_args.kwargs["params"]
            assert "startDateTime" in params

    @pytest.mark.asyncio
    async def test_create_event(self, client: GraphClient):
        """Test creating calendar event."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "event-1", "subject": "Meeting"}

            await client.create_event(
                subject="Meeting",
                start_datetime="2024-01-20T10:00:00Z",
                end_datetime="2024-01-20T11:00:00Z",
                location="Room 101",
                attendees=["person@test.com"],
            )

            call_json = mock_request.call_args.kwargs["json"]
            assert call_json["subject"] == "Meeting"
            assert "location" in call_json
            assert "attendees" in call_json

    @pytest.mark.asyncio
    async def test_delete_event(self, client: GraphClient):
        """Test deleting event."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            await client.delete_event("event-123")

            mock_request.assert_called_once_with("DELETE", "/me/events/event-123")


class TestEmailOperations:
    """Tests for email operations."""

    @pytest.fixture
    def client(self) -> GraphClient:
        """Create a GraphClient instance."""
        return GraphClient("test-token")

    @pytest.mark.asyncio
    async def test_list_messages(self, client: GraphClient):
        """Test listing messages."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"value": [{"subject": "Test"}]}

            await client.list_messages(folder="inbox", top=10, skip=0)

            mock_request.assert_called_once()
            assert "/mailFolders/inbox/messages" in str(mock_request.call_args)

    @pytest.mark.asyncio
    async def test_get_message(self, client: GraphClient):
        """Test getting single message."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "msg-1", "subject": "Test", "body": {}}

            await client.get_message("msg-1")

            mock_request.assert_called_once_with("GET", "/me/messages/msg-1")

    @pytest.mark.asyncio
    async def test_search_messages(self, client: GraphClient):
        """Test searching messages."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"value": []}

            await client.search_messages("test query", top=5)

            mock_request.assert_called_once()
            params = mock_request.call_args.kwargs["params"]
            assert '"test query"' in params["$search"]
