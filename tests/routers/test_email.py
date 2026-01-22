"""Tests for the email router."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


class TestEmailEndpoints:
    """Tests for email endpoints."""

    def test_get_inbox_unauthenticated(self, client: TestClient):
        """Test getting inbox without authentication."""
        response = client.get("/email/inbox")
        assert response.status_code == 401

    def test_get_inbox(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting inbox messages."""
        with patch("routers.email.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/email/inbox")

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "count" in data
        assert len(data["messages"]) == 1

    def test_get_inbox_with_pagination(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting inbox with pagination."""
        with patch("routers.email.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/email/inbox?top=10&skip=5")

        assert response.status_code == 200

    def test_get_message(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting a specific message."""
        with patch("routers.email.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/email/message/msg-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "msg-1"
        assert data["subject"] == "Test Email"
        assert "body" in data

    def test_search_emails(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test searching emails."""
        with patch("routers.email.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/email/search?query=test")

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert data["query"] == "test"
        assert "messages" in data

    def test_get_folders(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting mail folders."""
        mock_graph_client._request = AsyncMock(
            return_value={
                "value": [
                    {
                        "id": "inbox-id",
                        "displayName": "Inbox",
                        "unreadItemCount": 5,
                        "totalItemCount": 100,
                    },
                    {
                        "id": "sent-id",
                        "displayName": "Sent Items",
                        "unreadItemCount": 0,
                        "totalItemCount": 50,
                    },
                ]
            }
        )

        with patch("routers.email.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/email/folders")

        assert response.status_code == 200
        data = response.json()
        assert "folders" in data
        assert len(data["folders"]) == 2


class TestEmailFormatting:
    """Tests for email data formatting."""

    def test_email_summary_format(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test that email summary is formatted correctly."""
        with patch("routers.email.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/email/inbox")

        assert response.status_code == 200
        data = response.json()
        message = data["messages"][0]

        # Check required fields are present
        assert "id" in message
        assert "subject" in message
        assert "from_name" in message
        assert "from_email" in message
        assert "received" in message
        assert "is_read" in message
        assert "preview" in message

    def test_email_detail_format(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test that email detail is formatted correctly."""
        with patch("routers.email.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/email/message/msg-1")

        assert response.status_code == 200
        data = response.json()

        # Check all detail fields
        assert "id" in data
        assert "subject" in data
        assert "from_name" in data
        assert "from_email" in data
        assert "to" in data
        assert "received" in data
        assert "is_read" in data
        assert "body" in data
        assert "body_type" in data
        assert "has_attachments" in data
