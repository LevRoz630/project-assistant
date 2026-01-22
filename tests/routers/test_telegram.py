"""Tests for the Telegram router."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestTelegramStatus:
    """Tests for Telegram status endpoint."""

    def test_status_unauthenticated(self, client: TestClient):
        """Test status check without app authentication."""
        response = client.get("/telegram/status")
        assert response.status_code == 401

    def test_status_not_connected(
        self,
        authenticated_client: TestClient,
    ):
        """Test status when Telegram not connected."""
        with patch("routers.telegram.telegram.is_authenticated", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = False
            response = authenticated_client.get("/telegram/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    def test_status_connected(
        self,
        authenticated_client: TestClient,
    ):
        """Test status when Telegram is connected."""
        mock_client = MagicMock()
        mock_me = MagicMock()
        mock_me.id = 12345
        mock_me.username = "testuser"
        mock_me.first_name = "Test"
        mock_me.phone = "+1234567890"
        mock_client.get_me = AsyncMock(return_value=mock_me)

        with patch("routers.telegram.telegram.is_authenticated", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = True
            with patch("routers.telegram.telegram.get_client", new_callable=AsyncMock) as mock_get_client:
                mock_get_client.return_value = mock_client
                response = authenticated_client.get("/telegram/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["username"] == "testuser"


class TestTelegramAuth:
    """Tests for Telegram authentication endpoints."""

    def test_start_auth_no_phone(
        self,
        authenticated_client: TestClient,
    ):
        """Test starting auth without phone number."""
        with patch("routers.telegram.telegram.start_auth", new_callable=AsyncMock) as mock_start:
            mock_start.side_effect = ValueError("Phone number not provided")
            response = authenticated_client.post(
                "/telegram/auth/start",
                json={},
            )

        assert response.status_code == 400

    def test_start_auth_success(
        self,
        authenticated_client: TestClient,
    ):
        """Test starting auth successfully."""
        with patch("routers.telegram.telegram.start_auth", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = {"status": "code_sent", "phone": "+1234567890"}
            response = authenticated_client.post(
                "/telegram/auth/start",
                json={"phone": "+1234567890"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "code_sent"

    def test_complete_auth_success(
        self,
        authenticated_client: TestClient,
    ):
        """Test completing auth successfully."""
        with patch("routers.telegram.telegram.complete_auth", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = {
                "status": "authenticated",
                "user": {"id": 12345, "username": "testuser", "first_name": "Test"},
            }
            response = authenticated_client.post(
                "/telegram/auth/complete",
                json={"phone": "+1234567890", "code": "12345"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "authenticated"


class TestTelegramDialogs:
    """Tests for Telegram dialogs endpoints."""

    def test_get_dialogs(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting dialogs."""
        mock_dialogs = [
            {
                "id": 1,
                "entity": {"type": "user", "id": 100, "name": "John"},
                "name": "John",
                "unread_count": 5,
                "last_message": "Hello",
                "last_message_date": "2024-01-15T10:00:00",
                "is_pinned": False,
                "is_muted": False,
            }
        ]

        with patch("routers.telegram.telegram.get_dialogs", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_dialogs
            response = authenticated_client.get("/telegram/dialogs")

        assert response.status_code == 200
        data = response.json()
        assert "dialogs" in data
        assert data["count"] == 1

    def test_get_dialogs_unread_only(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting only unread dialogs."""
        with patch("routers.telegram.telegram.get_dialogs", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = authenticated_client.get("/telegram/dialogs?unread_only=true")

        assert response.status_code == 200
        mock_get.assert_called_once_with(limit=50, unread_only=True)


class TestTelegramMessages:
    """Tests for Telegram messages endpoints."""

    def test_get_unread_messages(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting unread messages."""
        mock_messages = [
            {
                "chat": {"type": "user", "id": 100, "name": "John"},
                "unread_count": 3,
                "messages": [
                    {"id": 1, "text": "Hello", "date": "2024-01-15T10:00:00"},
                ],
            }
        ]

        with patch("routers.telegram.telegram.get_unread_messages", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_messages
            response = authenticated_client.get("/telegram/unread")

        assert response.status_code == 200
        data = response.json()
        assert data["chats_with_unread"] == 1
        assert data["total_unread"] == 3

    def test_get_messages_from_chat(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting messages from specific chat."""
        mock_messages = [
            {"id": 1, "text": "Hello", "date": "2024-01-15T10:00:00"},
            {"id": 2, "text": "Hi there", "date": "2024-01-15T10:01:00"},
        ]

        with patch("routers.telegram.telegram.get_messages", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_messages
            response = authenticated_client.get("/telegram/messages/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["chat_id"] == 12345
        assert data["count"] == 2

    def test_mark_as_read(
        self,
        authenticated_client: TestClient,
    ):
        """Test marking messages as read."""
        with patch("routers.telegram.telegram.mark_as_read", new_callable=AsyncMock) as mock_mark:
            mock_mark.return_value = {"status": "marked_read", "chat_id": 12345}
            response = authenticated_client.post("/telegram/messages/12345/read")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "marked_read"


class TestTelegramSummary:
    """Tests for Telegram summary endpoint."""

    def test_get_summary(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting updates summary."""
        mock_summary = {
            "period_hours": 24,
            "since": "2024-01-14T10:00:00",
            "total_unread": 15,
            "chats_with_unread": 5,
            "channels": [],
            "groups": [{"id": 1, "name": "Group 1", "unread_count": 10}],
            "direct_messages": [{"id": 2, "name": "John", "unread_count": 5}],
        }

        with patch("routers.telegram.telegram.get_updates_summary", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_summary
            response = authenticated_client.get("/telegram/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_unread"] == 15
        assert data["chats_with_unread"] == 5
