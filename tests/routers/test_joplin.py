"""Tests for the Joplin router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_joplin_client():
    """Create a mock JoplinClient."""
    mock = MagicMock()
    mock.ping = AsyncMock(return_value=True)
    mock.list_notebooks = AsyncMock(
        return_value=[
            {
                "id": "nb-1",
                "title": "Diary",
                "parent_id": "",
                "created_time": 1705312800000,
                "updated_time": 1705399200000,
            },
            {
                "id": "nb-2",
                "title": "Projects",
                "parent_id": "",
                "created_time": 1705312800000,
                "updated_time": 1705399200000,
            },
        ]
    )
    mock.get_notebook_by_title = AsyncMock(
        return_value={"id": "nb-1", "title": "Diary"}
    )
    mock.create_notebook = AsyncMock(
        return_value={"id": "nb-new", "title": "New Notebook"}
    )
    mock.list_notes = AsyncMock(
        return_value=[
            {
                "id": "note-1",
                "title": "2024-01-15",
                "parent_id": "nb-1",
                "created_time": 1705312800000,
                "updated_time": 1705399200000,
                "is_todo": 0,
                "todo_completed": 0,
            }
        ]
    )
    mock.get_note = AsyncMock(
        return_value={
            "id": "note-1",
            "title": "Test Note",
            "body": "# Test\n\nContent here.",
            "parent_id": "nb-1",
            "created_time": 1705312800000,
            "updated_time": 1705399200000,
            "is_todo": 0,
        }
    )
    mock.create_note = AsyncMock(
        return_value={"id": "note-new", "title": "New Note"}
    )
    mock.update_note = AsyncMock(
        return_value={"id": "note-1", "title": "Updated Note"}
    )
    mock.delete_note = AsyncMock(return_value={"success": True})
    mock.search = AsyncMock(
        return_value=[
            {
                "id": "note-1",
                "title": "Test Note",
                "parent_id": "nb-1",
                "created_time": 1705312800000,
                "updated_time": 1705399200000,
            }
        ]
    )
    mock.list_tags = AsyncMock(
        return_value=[
            {"id": "tag-1", "title": "important"},
            {"id": "tag-2", "title": "work"},
        ]
    )
    mock.get_or_create_tag = AsyncMock(
        return_value={"id": "tag-1", "title": "important"}
    )
    mock.add_tag_to_note = AsyncMock(return_value={"success": True})
    mock.remove_tag_from_note = AsyncMock(return_value={"success": True})
    return mock


class TestJoplinStatus:
    """Tests for Joplin status endpoint."""

    def test_status_when_disabled(self, client: TestClient):
        """Test status when Joplin is disabled."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = False
            response = client.get("/joplin/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["connected"] is False

    def test_status_when_enabled_and_connected(self, client: TestClient, mock_joplin_client):
        """Test status when Joplin is enabled and connected."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = client.get("/joplin/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["connected"] is True


class TestJoplinNotebooks:
    """Tests for Joplin notebooks endpoints."""

    def test_list_notebooks_unauthenticated(self, client: TestClient):
        """Test listing notebooks without authentication."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            response = client.get("/joplin/notebooks")

        assert response.status_code == 401

    def test_list_notebooks(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test listing notebooks."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.get("/joplin/notebooks")

        assert response.status_code == 200
        data = response.json()
        assert "notebooks" in data
        assert len(data["notebooks"]) == 2
        titles = [nb["title"] for nb in data["notebooks"]]
        assert "Diary" in titles
        assert "Projects" in titles

    def test_create_notebook(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test creating a notebook."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.post(
                    "/joplin/notebooks",
                    params={"title": "New Notebook"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestJoplinNotes:
    """Tests for Joplin notes endpoints."""

    def test_list_notes(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test listing notes."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.get("/joplin/notes")

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data

    def test_list_notes_by_notebook(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test listing notes filtered by notebook."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.get("/joplin/notes", params={"notebook": "Diary"})

        assert response.status_code == 200
        data = response.json()
        assert data["notebook"] == "Diary"

    def test_get_note(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test getting a specific note."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.get("/joplin/notes/note-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "note-1"
        assert data["title"] == "Test Note"
        assert "body" in data

    def test_create_note(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test creating a note."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                with patch("routers.joplin.ingest_document", new_callable=AsyncMock):
                    response = authenticated_client.post(
                        "/joplin/notes",
                        json={
                            "notebook": "Diary",
                            "title": "New Note",
                            "body": "Content here",
                        },
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_update_note(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test updating a note."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                with patch("routers.joplin.ingest_document", new_callable=AsyncMock):
                    response = authenticated_client.put(
                        "/joplin/notes/note-1",
                        json={"body": "Updated content"},
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_note(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test deleting a note."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                with patch("routers.joplin.delete_document", new_callable=AsyncMock):
                    response = authenticated_client.delete("/joplin/notes/note-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestJoplinSearch:
    """Tests for Joplin search endpoint."""

    def test_search_notes(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test searching notes."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.get("/joplin/search", params={"q": "test"})

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert "results" in data


class TestJoplinTags:
    """Tests for Joplin tags endpoints."""

    def test_list_tags(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test listing tags."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.get("/joplin/tags")

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert len(data["tags"]) == 2

    def test_add_tag_to_note(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test adding a tag to a note."""
        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.post(
                    "/joplin/notes/note-1/tags",
                    params={"tag_name": "important"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tag"] == "important"


class TestJoplinDiary:
    """Tests for Joplin diary endpoint."""

    def test_create_today_diary_new(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test creating today's diary entry when it doesn't exist."""
        mock_joplin_client.list_notes = AsyncMock(return_value=[])  # No existing diary

        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                with patch("routers.joplin.ingest_document", new_callable=AsyncMock):
                    response = authenticated_client.post("/joplin/diary/today")

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        assert "body" in data

    def test_get_today_diary_existing(
        self,
        authenticated_client: TestClient,
        mock_joplin_client,
    ):
        """Test getting today's diary when it exists."""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        mock_joplin_client.list_notes = AsyncMock(
            return_value=[
                {
                    "id": "diary-today",
                    "title": today,
                    "parent_id": "nb-1",
                    "created_time": 1705312800000,
                    "updated_time": 1705399200000,
                    "is_todo": 0,
                }
            ]
        )
        mock_joplin_client.get_note = AsyncMock(
            return_value={
                "id": "diary-today",
                "title": today,
                "body": "# Today's entry",
                "parent_id": "nb-1",
            }
        )

        with patch("routers.joplin.settings") as mock_settings:
            mock_settings.joplin_enabled = True
            mock_settings.joplin_token = "test-token"
            with patch("routers.joplin.JoplinClient", return_value=mock_joplin_client):
                response = authenticated_client.post("/joplin/diary/today")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
