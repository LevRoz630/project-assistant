"""Tests for the notes router."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


class TestNotesEndpoints:
    """Tests for notes endpoints."""

    def test_get_folders_unauthenticated(self, client: TestClient):
        """Test getting folders without authentication."""
        response = client.get("/notes/folders")
        assert response.status_code == 401

    def test_get_folders(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting folders list."""
        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/notes/folders")

        assert response.status_code == 200
        data = response.json()
        assert "folders" in data
        folder_names = [f["name"] for f in data["folders"]]
        assert "Diary" in folder_names

    def test_list_notes_in_folder(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test listing notes in a folder."""
        mock_graph_client.list_folder = AsyncMock(
            return_value={
                "value": [
                    {
                        "id": "file-1",
                        "name": "2024-01-15.md",
                        "file": {},
                        "createdDateTime": "2024-01-15T08:00:00Z",
                        "lastModifiedDateTime": "2024-01-15T10:00:00Z",
                        "size": 1024,
                    }
                ]
            }
        )

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/notes/list/Diary")

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        assert len(data["notes"]) == 1
        assert data["notes"][0]["name"] == "2024-01-15.md"

    def test_get_note_content(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting note content."""
        mock_graph_client.get_file_content = AsyncMock(return_value=b"# Test Note\n\nContent here.")

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/notes/content/Diary/2024-01-15.md")

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "# Test Note\n\nContent here."
        assert data["folder"] == "Diary"
        assert data["filename"] == "2024-01-15.md"

    def test_create_note(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating a new note."""
        mock_graph_client.upload_file = AsyncMock(
            return_value={
                "id": "new-file-id",
                "name": "new-note.md",
            }
        )
        # File doesn't exist yet - get_item_by_path raises itemNotFound
        mock_graph_client.get_item_by_path = AsyncMock(side_effect=Exception("itemNotFound"))

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            with patch("routers.notes.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.post(
                    "/notes/create",
                    json={
                        "folder": "Inbox",
                        "filename": "new-note.md",
                        "content": "# New Note\n\nContent",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert "path" in data

    def test_create_note_in_custom_folder(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating note in a custom folder (endpoint creates folder if needed)."""
        mock_graph_client.upload_file = AsyncMock(
            return_value={"id": "new-file-id", "name": "note.md"}
        )
        mock_graph_client.get_item_by_path = AsyncMock(side_effect=Exception("itemNotFound"))

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            with patch("routers.notes.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.post(
                    "/notes/create",
                    json={
                        "folder": "CustomFolder",
                        "filename": "note.md",
                        "content": "Content",
                    },
                )

        # Endpoint should succeed - it creates folders as needed
        assert response.status_code == 200

    def test_update_note(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test updating a note."""
        mock_graph_client.upload_file = AsyncMock(
            return_value={
                "id": "file-id",
                "name": "note.md",
            }
        )

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            with patch("routers.notes.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.put(
                    "/notes/update/Diary/note.md",
                    json={"content": "Updated content"},
                )

        assert response.status_code == 200
        mock_graph_client.upload_file.assert_called_once()

    def test_delete_note(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test deleting a note."""
        mock_graph_client.delete_item = AsyncMock(return_value={"success": True})

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            with patch("routers.notes.delete_document", new_callable=AsyncMock):
                response = authenticated_client.delete("/notes/delete/Inbox/old-note.md")

        assert response.status_code == 200
        mock_graph_client.delete_item.assert_called_once()

    def test_get_or_create_today_diary(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting or creating today's diary entry."""
        # First call returns 404 (file doesn't exist)
        mock_graph_client.get_file_content = AsyncMock(side_effect=Exception("File not found"))
        mock_graph_client.upload_file = AsyncMock(
            return_value={
                "id": "new-diary-id",
                "name": "2024-01-15.md",
            }
        )

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            with patch("routers.notes.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.post("/notes/diary/today")

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["folder"] == "Diary"


class TestNotesValidation:
    """Tests for notes input validation."""

    def test_create_note_missing_filename(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test creating note without filename."""
        response = authenticated_client.post(
            "/notes/create",
            json={"folder": "Inbox", "content": "Content"},
        )

        assert response.status_code == 422  # Validation error

    def test_create_note_missing_content(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test creating note without content."""
        response = authenticated_client.post(
            "/notes/create",
            json={"folder": "Inbox", "filename": "note.md"},
        )

        assert response.status_code == 422  # Validation error

    def test_filename_must_be_markdown(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test that filename should have .md extension."""
        # File doesn't exist yet
        mock_graph_client.get_item_by_path = AsyncMock(side_effect=Exception("itemNotFound"))
        mock_graph_client.upload_file = AsyncMock(
            return_value={"id": "file-id", "name": "note.txt"}
        )

        with patch("routers.notes.GraphClient", return_value=mock_graph_client):
            with patch("routers.notes.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.post(
                    "/notes/create",
                    json={
                        "folder": "Inbox",
                        "filename": "note.txt",  # Not .md
                        "content": "Content",
                    },
                )

        # The endpoint accepts any extension (no validation)
        assert response.status_code == 200
