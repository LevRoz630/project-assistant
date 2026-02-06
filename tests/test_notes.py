"""Tests for notes router — CRUD, subfolder support, validation, and folder management."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Unit tests for validation helpers
# ---------------------------------------------------------------------------

class TestValidatePathComponent:
    """Tests for _validate_path_component."""

    def _validate(self, value, field="test", **kw):
        from backend.routers.notes import _validate_path_component
        return _validate_path_component(value, field, **kw)

    def test_valid_name(self):
        assert self._validate("Diary") == "Diary"

    def test_valid_filename(self):
        assert self._validate("my-note.md", is_filename=True) == "my-note.md"

    def test_empty_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("")
        assert exc_info.value.status_code == 400

    def test_path_traversal_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("..")
        assert "path_traversal" in str(exc_info.value.detail)

    def test_absolute_path_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("/etc/passwd")
        assert exc_info.value.status_code == 400

    def test_backslash_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("foo\\bar")
        assert exc_info.value.status_code == 400

    def test_null_byte_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("foo\x00bar")
        assert "null_byte" in str(exc_info.value.detail)

    def test_filename_too_long(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("x" * 101, is_filename=True)
        assert "too long" in str(exc_info.value.detail)

    def test_filename_invalid_chars(self):
        for ch in ':*?"<>|':
            with pytest.raises(HTTPException):
                self._validate(f"bad{ch}name.md", is_filename=True)

    def test_hidden_file_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate(".hidden", is_filename=True)
        assert "dot" in str(exc_info.value.detail).lower()


class TestValidateFolderPath:
    """Tests for _validate_folder_path."""

    def _validate(self, value, field="folder"):
        from backend.routers.notes import _validate_folder_path
        return _validate_folder_path(value, field)

    def test_single_segment(self):
        assert self._validate("Projects") == "Projects"

    def test_multi_segment(self):
        assert self._validate("Projects/SubA/SubB") == "Projects/SubA/SubB"

    def test_empty_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("")
        assert exc_info.value.status_code == 400

    def test_too_deep_raises(self):
        path = "/".join([f"level{i}" for i in range(7)])
        with pytest.raises(HTTPException) as exc_info:
            self._validate(path)
        assert "too deep" in str(exc_info.value.detail)

    def test_max_depth_allowed(self):
        path = "/".join([f"level{i}" for i in range(6)])
        assert self._validate(path) == path

    def test_empty_segment_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            self._validate("Projects//SubA")
        assert "empty path segment" in str(exc_info.value.detail)

    def test_traversal_in_segment_raises(self):
        with pytest.raises(HTTPException):
            self._validate("Projects/../etc")


class TestSplitItemPath:
    """Tests for _split_item_path."""

    def _split(self, path):
        from backend.routers.notes import _split_item_path
        return _split_item_path(path)

    def test_simple_path(self):
        folder, filename = self._split("Diary/note.md")
        assert folder == "Diary"
        assert filename == "note.md"

    def test_nested_path(self):
        folder, filename = self._split("Projects/SubA/design.md")
        assert folder == "Projects/SubA"
        assert filename == "design.md"

    def test_no_slash_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            self._split("orphan.md")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Integration tests for notes endpoints
# ---------------------------------------------------------------------------

@pytest.fixture
def _patch_notes_deps(mock_graph_client, mock_get_access_token):
    """Override the notes router graph client dependency with the mock."""
    from backend.main import app
    from backend.routers.notes import get_graph_client

    app.dependency_overrides[get_graph_client] = lambda: mock_graph_client
    yield
    app.dependency_overrides.pop(get_graph_client, None)


@pytest.fixture
def _patch_vectors():
    """Mock vector store operations so they don't touch real ChromaDB."""
    with (
        patch("backend.routers.notes.ingest_document", new_callable=AsyncMock) as mock_ingest,
        patch("backend.routers.notes.delete_document", new_callable=AsyncMock) as mock_delete,
    ):
        yield mock_ingest, mock_delete


class TestListFolders:
    """Tests for GET /notes/folders."""

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_list_folders(self, authenticated_client, mock_graph_client):
        res = authenticated_client.get("/notes/folders")
        assert res.status_code == 200
        data = res.json()
        assert "folders" in data
        names = [f["name"] for f in data["folders"]]
        assert "Diary" in names
        assert "Projects" in names

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_list_folders_excludes_hidden(self, authenticated_client, mock_graph_client):
        mock_graph_client.list_folder.return_value = {
            "value": [
                {"id": "1", "name": "Diary", "folder": {}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
                {"id": "2", "name": ".obsidian", "folder": {}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
                {"id": "3", "name": ".trash", "folder": {}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
            ]
        }
        res = authenticated_client.get("/notes/folders")
        assert res.status_code == 200
        names = [f["name"] for f in res.json()["folders"]]
        assert "Diary" in names
        assert ".obsidian" not in names
        assert ".trash" not in names

    def test_list_folders_unauthenticated(self, client):
        res = client.get("/notes/folders")
        assert res.status_code == 401


class TestListNotes:
    """Tests for GET /notes/list/{folder_path}."""

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_list_notes_in_folder(self, authenticated_client, mock_graph_client):
        mock_graph_client.list_folder.return_value = {
            "value": [
                {"id": "n1", "name": "note1.md", "file": {}, "size": 100, "createdDateTime": "2024-01-10T00:00:00Z", "lastModifiedDateTime": "2024-01-15T10:00:00Z"},
                {"id": "n2", "name": "note2.md", "file": {}, "size": 200, "createdDateTime": "2024-01-09T00:00:00Z", "lastModifiedDateTime": "2024-01-14T10:00:00Z"},
                {"id": "sf1", "name": "SubFolder", "folder": {"childCount": 3}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
                {"id": "h1", "name": ".hidden", "folder": {"childCount": 0}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
                {"id": "s1", "name": "_system", "folder": {"childCount": 0}, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
                {"id": "x1", "name": "image.png", "file": {}, "size": 5000, "createdDateTime": "2024-01-01T00:00:00Z", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
            ]
        }
        res = authenticated_client.get("/notes/list/Projects")
        assert res.status_code == 200
        data = res.json()
        assert data["folder"] == "Projects"
        # Only .md files
        assert len(data["notes"]) == 2
        assert data["notes"][0]["name"] == "note1.md"
        # Only visible subfolders (not hidden/system)
        assert len(data["subfolders"]) == 1
        assert data["subfolders"][0]["name"] == "SubFolder"
        assert data["subfolders"][0]["childCount"] == 3

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_list_notes_nested_folder(self, authenticated_client, mock_graph_client):
        mock_graph_client.list_folder.return_value = {"value": []}
        res = authenticated_client.get("/notes/list/Projects/SubA/SubB")
        assert res.status_code == 200
        assert res.json()["folder"] == "Projects/SubA/SubB"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_list_notes_folder_not_found(self, authenticated_client, mock_graph_client):
        mock_graph_client.list_folder.side_effect = Exception("itemNotFound")
        res = authenticated_client.get("/notes/list/NonExistent")
        assert res.status_code == 200
        data = res.json()
        assert data["notes"] == []
        assert data["subfolders"] == []

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_list_notes_path_traversal_rejected(self, authenticated_client):
        # URL-encode the dots so the HTTP client doesn't normalize the path
        res = authenticated_client.get("/notes/list/Projects/%2e%2e/etc")
        assert res.status_code == 400


class TestGetNote:
    """Tests for GET /notes/content/{item_path}."""

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_get_note_content(self, authenticated_client, mock_graph_client):
        mock_graph_client.get_file_content.return_value = b"# Hello\n\nWorld"
        mock_graph_client.get_item_by_path.return_value = {
            "createdDateTime": "2024-01-15T08:00:00Z",
            "lastModifiedDateTime": "2024-01-15T10:00:00Z",
        }
        res = authenticated_client.get("/notes/content/Diary/test.md")
        assert res.status_code == 200
        data = res.json()
        assert data["content"] == "# Hello\n\nWorld"
        assert data["folder"] == "Diary"
        assert data["filename"] == "test.md"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_get_note_nested_folder(self, authenticated_client, mock_graph_client):
        mock_graph_client.get_file_content.return_value = b"nested content"
        mock_graph_client.get_item_by_path.return_value = {
            "createdDateTime": "2024-01-15T08:00:00Z",
            "lastModifiedDateTime": "2024-01-15T10:00:00Z",
        }
        res = authenticated_client.get("/notes/content/Projects/SubA/design.md")
        assert res.status_code == 200
        data = res.json()
        assert data["folder"] == "Projects/SubA"
        assert data["filename"] == "design.md"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_get_note_not_found(self, authenticated_client, mock_graph_client):
        mock_graph_client.get_file_content.side_effect = Exception("itemNotFound: resource not found")
        res = authenticated_client.get("/notes/content/Diary/missing.md")
        assert res.status_code == 404


class TestCreateNote:
    """Tests for POST /notes/create."""

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_create_note(self, authenticated_client, mock_graph_client):
        # get_item_by_path should 404 first (file doesn't exist yet), then succeed for folder check
        mock_graph_client.get_item_by_path.side_effect = Exception("itemNotFound")
        mock_graph_client.upload_file.return_value = {"id": "new-file", "name": "my-note.md"}

        res = authenticated_client.post("/notes/create", json={
            "folder": "Projects",
            "filename": "my-note.md",
            "content": "# My Note\n",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["filename"] == "my-note.md"

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_create_note_in_subfolder(self, authenticated_client, mock_graph_client):
        mock_graph_client.get_item_by_path.side_effect = Exception("itemNotFound")
        mock_graph_client.upload_file.return_value = {"id": "new-file", "name": "design.md"}

        res = authenticated_client.post("/notes/create", json={
            "folder": "Projects/WebApp",
            "filename": "design.md",
            "content": "# Design Doc\n",
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_create_note_auto_appends_md(self, authenticated_client, mock_graph_client):
        mock_graph_client.get_item_by_path.side_effect = Exception("itemNotFound")
        mock_graph_client.upload_file.return_value = {"id": "new-file", "name": "my-note.md"}

        res = authenticated_client.post("/notes/create", json={
            "folder": "Diary",
            "filename": "my-note",
            "content": "# Note\n",
        })
        assert res.status_code == 200
        assert res.json()["filename"] == "my-note.md"

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_create_note_already_exists(self, authenticated_client, mock_graph_client):
        # get_item_by_path succeeds = file exists
        mock_graph_client.get_item_by_path.return_value = {"id": "existing"}

        res = authenticated_client.post("/notes/create", json={
            "folder": "Diary",
            "filename": "existing.md",
            "content": "content",
        })
        assert res.status_code == 409
        assert res.json()["detail"]["code"] == "already_exists"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_note_invalid_folder(self, authenticated_client):
        res = authenticated_client.post("/notes/create", json={
            "folder": "../etc",
            "filename": "hack.md",
            "content": "bad",
        })
        assert res.status_code == 400


class TestUpdateNote:
    """Tests for PUT /notes/update/{item_path}."""

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_update_note(self, authenticated_client, mock_graph_client):
        mock_graph_client.upload_file.return_value = {"id": "file-123"}

        res = authenticated_client.put("/notes/update/Diary/note.md", json={
            "content": "updated content",
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_update_note_nested(self, authenticated_client, mock_graph_client):
        mock_graph_client.upload_file.return_value = {"id": "file-123"}

        res = authenticated_client.put("/notes/update/Projects/SubA/doc.md", json={
            "content": "updated",
        })
        assert res.status_code == 200

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_update_note_not_found(self, authenticated_client, mock_graph_client):
        mock_graph_client.upload_file.side_effect = Exception("itemNotFound")

        res = authenticated_client.put("/notes/update/Diary/missing.md", json={
            "content": "oops",
        })
        assert res.status_code == 404


class TestDeleteNote:
    """Tests for DELETE /notes/delete/{item_path}."""

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_delete_note(self, authenticated_client, mock_graph_client):
        res = authenticated_client.delete("/notes/delete/Diary/old.md")
        assert res.status_code == 200
        assert res.json()["success"] is True

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_delete_note_nested(self, authenticated_client, mock_graph_client):
        res = authenticated_client.delete("/notes/delete/Projects/SubA/old.md")
        assert res.status_code == 200

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_delete_note_not_found(self, authenticated_client, mock_graph_client):
        mock_graph_client.delete_item.side_effect = Exception("itemNotFound")

        res = authenticated_client.delete("/notes/delete/Diary/ghost.md")
        assert res.status_code == 404


class TestMoveNote:
    """Tests for POST /notes/move/{item_path}."""

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_move_note(self, authenticated_client, mock_graph_client):
        mock_graph_client.move_item = AsyncMock(return_value={"id": "moved"})
        mock_graph_client.get_file_content.return_value = b"content"

        res = authenticated_client.post("/notes/move/Diary/note.md", json={
            "target_folder": "Projects",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["new_folder"] == "Projects"

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_move_note_to_subfolder(self, authenticated_client, mock_graph_client):
        mock_graph_client.move_item = AsyncMock(return_value={"id": "moved"})
        mock_graph_client.get_file_content.return_value = b"content"

        res = authenticated_client.post("/notes/move/Diary/note.md", json={
            "target_folder": "Projects/SubA",
        })
        assert res.status_code == 200
        assert res.json()["new_folder"] == "Projects/SubA"

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_move_note_same_folder_rejected(self, authenticated_client):
        res = authenticated_client.post("/notes/move/Diary/note.md", json={
            "target_folder": "Diary",
        })
        assert res.status_code == 400
        assert res.json()["detail"]["code"] == "same_folder"


class TestCreateFolder:
    """Tests for POST /notes/create-folder."""

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_subfolder(self, authenticated_client, mock_graph_client):
        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "Projects",
            "name": "WebApp",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["name"] == "WebApp"
        assert data["path"] == "Projects/WebApp"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_top_level_folder(self, authenticated_client, mock_graph_client):
        """Empty parent_path should create folder at top level."""
        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "",
            "name": "Archive",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["name"] == "Archive"
        assert data["path"] == "Archive"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_folder_no_parent_path_field(self, authenticated_client, mock_graph_client):
        """parent_path defaults to empty string when omitted."""
        res = authenticated_client.post("/notes/create-folder", json={
            "name": "NewTopFolder",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["path"] == "NewTopFolder"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_deeply_nested_folder(self, authenticated_client, mock_graph_client):
        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "Projects/SubA/SubB",
            "name": "SubC",
        })
        assert res.status_code == 200
        assert res.json()["path"] == "Projects/SubA/SubB/SubC"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_folder_hidden_name_rejected(self, authenticated_client):
        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "Projects",
            "name": ".hidden",
        })
        assert res.status_code == 400
        assert "invalid_name" in str(res.json())

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_folder_underscore_name_rejected(self, authenticated_client):
        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "Projects",
            "name": "_system",
        })
        assert res.status_code == 400

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_folder_already_exists(self, authenticated_client, mock_graph_client):
        mock_graph_client.create_folder.side_effect = Exception("nameAlreadyExists")

        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "Projects",
            "name": "Existing",
        })
        assert res.status_code == 409
        assert res.json()["detail"]["code"] == "already_exists"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_folder_parent_not_found(self, authenticated_client, mock_graph_client):
        mock_graph_client.create_folder.side_effect = Exception("itemNotFound: parent does not exist")

        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "NonExistent",
            "name": "Child",
        })
        assert res.status_code == 404
        assert res.json()["detail"]["code"] == "parent_not_found"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_folder_empty_name_rejected(self, authenticated_client):
        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "Projects",
            "name": "",
        })
        assert res.status_code == 400

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_create_folder_traversal_in_parent(self, authenticated_client):
        res = authenticated_client.post("/notes/create-folder", json={
            "parent_path": "Projects/../etc",
            "name": "Hack",
        })
        assert res.status_code == 400


class TestFolderTree:
    """Tests for GET /notes/folder-tree."""

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_folder_tree(self, authenticated_client, mock_graph_client):
        # Root level: two folders
        def list_folder_side_effect(path):
            if path == "PersonalAI":
                return {
                    "value": [
                        {"name": "Diary", "folder": {"childCount": 2}},
                        {"name": "Projects", "folder": {"childCount": 1}},
                        {"name": ".obsidian", "folder": {"childCount": 5}},
                    ]
                }
            if path == "PersonalAI/Diary":
                return {"value": []}
            if path == "PersonalAI/Projects":
                return {
                    "value": [
                        {"name": "WebApp", "folder": {"childCount": 0}},
                        {"name": "readme.md", "file": {}, "size": 100},
                    ]
                }
            if path == "PersonalAI/Projects/WebApp":
                return {"value": []}
            return {"value": []}

        mock_graph_client.list_folder = AsyncMock(side_effect=list_folder_side_effect)

        res = authenticated_client.get("/notes/folder-tree")
        assert res.status_code == 200
        tree = res.json()["tree"]
        names = [n["name"] for n in tree]
        assert "Diary" in names
        assert "Projects" in names
        assert ".obsidian" not in names

        # Projects should have WebApp child
        projects = next(n for n in tree if n["name"] == "Projects")
        assert len(projects["children"]) == 1
        assert projects["children"][0]["name"] == "WebApp"
        assert projects["children"][0]["path"] == "Projects/WebApp"

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_folder_tree_empty(self, authenticated_client, mock_graph_client):
        mock_graph_client.list_folder.return_value = {"value": []}
        res = authenticated_client.get("/notes/folder-tree")
        assert res.status_code == 200
        assert res.json()["tree"] == []


class TestDiaryToday:
    """Tests for POST /notes/diary/today."""

    @pytest.mark.usefixtures("_patch_notes_deps", "_patch_vectors")
    def test_diary_today_creates_new(self, authenticated_client, mock_graph_client):
        mock_graph_client.get_file_content.side_effect = Exception("itemNotFound")
        mock_graph_client.upload_file.return_value = {"id": "diary-new"}

        res = authenticated_client.post("/notes/diary/today")
        assert res.status_code == 200
        data = res.json()
        assert data["created"] is True
        assert data["filename"].endswith(".md")

    @pytest.mark.usefixtures("_patch_notes_deps")
    def test_diary_today_returns_existing(self, authenticated_client, mock_graph_client):
        mock_graph_client.get_file_content.return_value = b"# 2026-02-06\n\nexisting diary"

        res = authenticated_client.post("/notes/diary/today")
        assert res.status_code == 200
        data = res.json()
        assert data["exists"] is True
        assert "existing diary" in data["content"]
