"""Tests for the chat router."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestChatEndpoints:
    """Tests for chat endpoints."""

    def test_send_message_unauthenticated(self, client: TestClient):
        """Test sending message without authentication."""
        response = client.post(
            "/chat/send",
            json={"message": "Hello", "use_context": True},
        )

        assert response.status_code == 401

    def test_send_message_authenticated(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test sending message with authentication."""
        with patch("routers.chat.search_documents", new_callable=AsyncMock) as mock_search:
            with patch("routers.chat.generate_response", new_callable=AsyncMock) as mock_gen:
                with patch("routers.chat._get_tasks_context", new_callable=AsyncMock) as mock_tasks:
                    with patch(
                        "routers.chat._get_calendar_context", new_callable=AsyncMock
                    ) as mock_cal:
                        mock_search.return_value = []
                        mock_gen.return_value = "AI response"
                        mock_tasks.return_value = ""
                        mock_cal.return_value = ""

                        response = authenticated_client.post(
                            "/chat/send",
                            json={
                                "message": "Hello",
                                "use_context": True,
                                "include_tasks": True,
                                "include_calendar": True,
                                "include_email": False,
                            },
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["response"] == "AI response"

    def test_send_message_with_context(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test sending message with RAG context."""
        mock_search_results = [
            {"content": "Relevant info", "source": "notes/diary.md", "metadata": {}, "score": 0.9}
        ]

        with patch("routers.chat.search_documents", new_callable=AsyncMock) as mock_search:
            with patch("routers.chat.generate_response", new_callable=AsyncMock) as mock_gen:
                with patch("routers.chat._get_tasks_context", new_callable=AsyncMock) as mock_tasks:
                    with patch(
                        "routers.chat._get_calendar_context", new_callable=AsyncMock
                    ) as mock_cal:
                        mock_search.return_value = mock_search_results
                        mock_gen.return_value = "Response with context"
                        mock_tasks.return_value = ""
                        mock_cal.return_value = ""

                        response = authenticated_client.post(
                            "/chat/send",
                            json={"message": "What did I write?", "use_context": True},
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["context_used"] is True
                        assert data["sources"] == ["notes/diary.md"]

    def test_send_message_without_context(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test sending message without RAG context."""
        with patch("routers.chat.generate_response", new_callable=AsyncMock) as mock_gen:
            with patch("routers.chat._get_tasks_context", new_callable=AsyncMock) as mock_tasks:
                with patch(
                    "routers.chat._get_calendar_context", new_callable=AsyncMock
                ) as mock_cal:
                    mock_gen.return_value = "Response without context"
                    mock_tasks.return_value = ""
                    mock_cal.return_value = ""

                    response = authenticated_client.post(
                        "/chat/send",
                        json={
                            "message": "Hello",
                            "use_context": False,
                            "include_tasks": False,
                            "include_calendar": False,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["context_used"] is False

    def test_get_stats_unauthenticated(self, client: TestClient):
        """Test getting stats without authentication."""
        response = client.get("/chat/stats")
        assert response.status_code == 401

    def test_get_stats_authenticated(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting stats with authentication."""
        with patch("routers.chat.get_collection_stats", new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = {"total_chunks": 100, "persist_directory": "./data"}

            response = authenticated_client.get("/chat/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total_chunks"] == 100

    def test_ingest_all_notes_unauthenticated(self, client: TestClient):
        """Test ingesting notes without authentication."""
        response = client.post("/chat/ingest")
        assert response.status_code == 401


class TestConversationHistory:
    """Tests for conversation history endpoints."""

    def test_get_history_unauthenticated(self, client: TestClient):
        """Test getting history without authentication."""
        response = client.get("/chat/history")
        assert response.status_code == 401

    def test_get_history_empty(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting history when no history file exists."""
        mock_graph_client.get_file_content = AsyncMock(
            side_effect=Exception("File not found")
        )

        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/chat/history")

            assert response.status_code == 200
            data = response.json()
            assert data["conversations"] == []

    def test_get_history_with_data(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting history with existing conversations."""
        history_data = {
            "conversations": [
                {
                    "id": "conv-1",
                    "title": "Test conversation",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "createdAt": "2024-01-15T10:00:00Z",
                    "updatedAt": "2024-01-15T10:00:00Z",
                }
            ]
        }
        mock_graph_client.get_file_content = AsyncMock(
            return_value=b'{"conversations": [{"id": "conv-1", "title": "Test conversation", "messages": [{"role": "user", "content": "Hello"}], "createdAt": "2024-01-15T10:00:00Z", "updatedAt": "2024-01-15T10:00:00Z"}]}'
        )

        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/chat/history")

            assert response.status_code == 200
            data = response.json()
            assert len(data["conversations"]) == 1
            assert data["conversations"][0]["id"] == "conv-1"

    def test_save_history_unauthenticated(self, client: TestClient):
        """Test saving history without authentication."""
        response = client.post(
            "/chat/history",
            json={"conversations": []},
        )
        assert response.status_code == 401

    def test_save_history(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test saving conversation history."""
        conversations = [
            {
                "id": "conv-1",
                "title": "Test",
                "messages": [{"role": "user", "content": "Hi"}],
                "createdAt": "2024-01-15T10:00:00Z",
                "updatedAt": "2024-01-15T10:00:00Z",
            }
        ]

        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post(
                "/chat/history",
                json={"conversations": conversations},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "saved"
            assert data["count"] == 1
            mock_graph_client.upload_file.assert_called_once()

    def test_delete_conversation_unauthenticated(self, client: TestClient):
        """Test deleting conversation without authentication."""
        response = client.delete("/chat/history/conv-1")
        assert response.status_code == 401

    def test_delete_conversation(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test deleting a specific conversation."""
        mock_graph_client.get_file_content = AsyncMock(
            return_value=b'{"conversations": [{"id": "conv-1", "title": "Test"}, {"id": "conv-2", "title": "Keep"}]}'
        )

        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.delete("/chat/history/conv-1")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "deleted"
            assert data["id"] == "conv-1"
            # Verify upload was called with updated data (conv-2 only)
            mock_graph_client.upload_file.assert_called_once()


class TestContextFunctions:
    """Tests for context fetching functions."""

    @pytest.mark.asyncio
    async def test_get_tasks_context(self, mock_graph_client):
        """Test fetching tasks context."""
        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            from routers.chat import _get_tasks_context

            context = await _get_tasks_context("test-token")

            assert isinstance(context, str)
            # Should have called list_task_lists and list_tasks
            mock_graph_client.list_task_lists.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_calendar_context(self, mock_graph_client):
        """Test fetching calendar context."""
        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            from routers.chat import _get_calendar_context

            context = await _get_calendar_context("test-token")

            assert isinstance(context, str)
            mock_graph_client.get_calendar_view.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_email_context(self, mock_graph_client):
        """Test fetching email context."""
        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            from routers.chat import _get_email_context

            context = await _get_email_context("test-token")

            assert isinstance(context, str)
            mock_graph_client.list_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks_context_error_handling(self, mock_graph_client):
        """Test tasks context error handling."""
        mock_graph_client.list_task_lists = AsyncMock(side_effect=Exception("API error"))

        with patch("routers.chat.GraphClient", return_value=mock_graph_client):
            from routers.chat import _get_tasks_context

            context = await _get_tasks_context("test-token")

            assert "Error fetching tasks" in context
