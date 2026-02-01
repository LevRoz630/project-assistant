"""Tests for the calendar router."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestCalendarEndpoints:
    """Tests for calendar endpoints."""

    def test_get_today_unauthenticated(self, client: TestClient):
        """Test getting today's events without authentication."""
        response = client.get("/calendar/today")
        assert response.status_code == 401

    def test_get_today_events(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting today's calendar events."""
        with patch("routers.calendar.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/calendar/today")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_get_week_events(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting week's calendar events."""
        with patch("routers.calendar.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/calendar/week")

        assert response.status_code == 200
        data = response.json()
        assert "events_by_date" in data

    def test_list_calendars(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test listing calendars."""
        mock_graph_client.list_calendars = AsyncMock(
            return_value={
                "value": [
                    {
                        "id": "cal-1",
                        "name": "Calendar",
                        "color": "blue",
                        "isDefaultCalendar": True,
                        "canEdit": True,
                    }
                ]
            }
        )

        with patch("routers.calendar.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/calendar/list")

        assert response.status_code == 200
        data = response.json()
        assert "calendars" in data

    def test_create_event(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating a calendar event."""
        mock_graph_client.create_event = AsyncMock(
            return_value={
                "id": "event-new",
                "subject": "Test Event",
                "start": {"dateTime": "2024-01-20T10:00:00"},
                "end": {"dateTime": "2024-01-20T11:00:00"},
                "webLink": "https://outlook.com/event",
            }
        )

        with patch("routers.calendar.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post(
                "/calendar/create",
                json={
                    "subject": "Test Event",
                    "start": "2024-01-20T10:00:00",
                    "end": "2024-01-20T11:00:00",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event"]["id"] == "event-new"

    def test_delete_event(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test deleting a calendar event."""
        with patch("routers.calendar.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.delete("/calendar/delete/event-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_graph_client.delete_event.assert_called_once_with("event-1")


class TestCalendarCacheInvalidation:
    """Tests for cache invalidation on calendar mutations."""

    def test_create_event_invalidates_cache(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
        mock_session_id,
    ):
        """Test that creating an event invalidates the calendar cache."""
        mock_graph_client.create_event = AsyncMock(
            return_value={
                "id": "event-new",
                "subject": "Test Event",
                "start": {"dateTime": "2024-01-20T10:00:00"},
                "end": {"dateTime": "2024-01-20T11:00:00"},
            }
        )
        mock_invalidate = MagicMock()

        with (
            patch("routers.calendar.GraphClient", return_value=mock_graph_client),
            patch("routers.calendar.invalidate_context", mock_invalidate),
        ):
            response = authenticated_client.post(
                "/calendar/create",
                json={
                    "subject": "Test Event",
                    "start": "2024-01-20T10:00:00",
                    "end": "2024-01-20T11:00:00",
                },
            )

        assert response.status_code == 200
        mock_invalidate.assert_called_once_with("calendar", mock_session_id)

    def test_delete_event_invalidates_cache(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
        mock_session_id,
    ):
        """Test that deleting an event invalidates the calendar cache."""
        mock_invalidate = MagicMock()

        with (
            patch("routers.calendar.GraphClient", return_value=mock_graph_client),
            patch("routers.calendar.invalidate_context", mock_invalidate),
        ):
            response = authenticated_client.delete("/calendar/delete/event-1")

        assert response.status_code == 200
        mock_invalidate.assert_called_once_with("calendar", mock_session_id)


class TestCalendarValidation:
    """Tests for calendar input validation."""

    def test_get_range_invalid_date_format(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting events with invalid date format."""
        response = authenticated_client.get(
            "/calendar/range?start_date=invalid&end_date=2024-01-20"
        )
        assert response.status_code == 400

    def test_create_event_missing_required_fields(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test creating event without required fields."""
        response = authenticated_client.post(
            "/calendar/create",
            json={"subject": "Test Event"},  # Missing start and end
        )
        assert response.status_code == 422
