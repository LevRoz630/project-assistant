"""Tests for the OneNote router."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


class TestOneNoteNotebooks:
    """Tests for OneNote notebooks endpoints."""

    def test_list_notebooks_unauthenticated(self, client: TestClient):
        """Test listing notebooks without authentication."""
        response = client.get("/onenote/notebooks")
        assert response.status_code == 401

    def test_list_notebooks(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test listing notebooks."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/onenote/notebooks")

        assert response.status_code == 200
        data = response.json()
        assert "notebooks" in data
        assert len(data["notebooks"]) == 1
        assert data["notebooks"][0]["name"] == "PersonalAI"

    def test_create_notebook(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating a notebook."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post(
                "/onenote/notebooks",
                params={"name": "New Notebook"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestOneNoteSections:
    """Tests for OneNote sections endpoints."""

    def test_list_sections(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test listing sections in a notebook."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/onenote/notebooks/notebook-1/sections")

        assert response.status_code == 200
        data = response.json()
        assert "sections" in data
        assert len(data["sections"]) == 1
        assert data["sections"][0]["name"] == "Diary"

    def test_create_section(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating a section."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post(
                "/onenote/notebooks/notebook-1/sections",
                params={"name": "New Section"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestOneNotePages:
    """Tests for OneNote pages endpoints."""

    def test_list_pages_in_section(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test listing pages in a section."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/onenote/sections/section-1/pages")

        assert response.status_code == 200
        data = response.json()
        assert "pages" in data

    def test_list_all_pages(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test listing all recent pages."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/onenote/pages")

        assert response.status_code == 200
        data = response.json()
        assert "pages" in data

    def test_get_page(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting a page with content converted to markdown."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/onenote/pages/page-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "page-1"
        assert "content" in data
        # Content should be converted to markdown
        assert "# Test" in data["content"]

    def test_create_page(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating a page with markdown content."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            with patch("routers.onenote.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.post(
                    "/onenote/pages",
                    json={
                        "section_id": "section-1",
                        "title": "New Page",
                        "content": "# Hello\n\nThis is markdown.",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_update_page(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test updating a page."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            with patch("routers.onenote.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.patch(
                    "/onenote/pages/page-1",
                    json={"content": "Updated content"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_page(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test deleting a page."""
        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            with patch("routers.onenote.delete_document", new_callable=AsyncMock):
                response = authenticated_client.delete("/onenote/pages/page-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestOneNoteDiary:
    """Tests for OneNote diary endpoint."""

    def test_create_today_diary_new(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating today's diary when it doesn't exist."""
        # No existing pages
        mock_graph_client.list_pages = AsyncMock(return_value={"value": []})

        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            with patch("routers.onenote.ingest_document", new_callable=AsyncMock):
                response = authenticated_client.post("/onenote/diary/today")

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        assert "content" in data

    def test_get_today_diary_existing(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting today's diary when it exists."""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        mock_graph_client.list_pages = AsyncMock(
            return_value={
                "value": [
                    {
                        "id": "diary-today",
                        "title": today,
                        "createdDateTime": "2024-01-15T08:00:00Z",
                        "lastModifiedDateTime": "2024-01-15T10:00:00Z",
                    }
                ]
            }
        )
        mock_graph_client.get_page_content = AsyncMock(
            return_value="<html><body><h1>Today</h1><p>Entry content</p></body></html>"
        )

        with patch("routers.onenote.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post("/onenote/diary/today")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True


class TestMarkdownConversion:
    """Tests for HTML/Markdown conversion."""

    def test_markdown_to_html_headers(self):
        """Test markdown headers convert to HTML."""
        from routers.onenote import markdown_to_html

        result = markdown_to_html("# Header 1\n## Header 2\n### Header 3")
        assert "<h1>Header 1</h1>" in result
        assert "<h2>Header 2</h2>" in result
        assert "<h3>Header 3</h3>" in result

    def test_markdown_to_html_lists(self):
        """Test markdown lists convert to HTML."""
        from routers.onenote import markdown_to_html

        result = markdown_to_html("- Item 1\n- Item 2")
        assert "<li>Item 1</li>" in result
        assert "<li>Item 2</li>" in result

    def test_html_to_markdown_headers(self):
        """Test HTML headers convert to markdown."""
        from routers.onenote import html_to_markdown

        result = html_to_markdown("<h1>Header 1</h1><h2>Header 2</h2>")
        assert "# Header 1" in result
        assert "## Header 2" in result

    def test_html_to_markdown_paragraphs(self):
        """Test HTML paragraphs convert to markdown."""
        from routers.onenote import html_to_markdown

        result = html_to_markdown("<p>Paragraph 1</p><p>Paragraph 2</p>")
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result
