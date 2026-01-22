"""Tests for the sync router."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from services.sync import get_scheduler, get_sync_state


class TestSyncEndpoints:
    """Tests for sync endpoints."""

    @pytest.fixture(autouse=True)
    def reset_sync_state(self):
        """Reset sync state before each test."""
        state = get_sync_state()
        state.is_syncing = False
        state.last_sync = None
        state.indexed_files = {}
        state.errors = []

        scheduler = get_scheduler()
        scheduler.stop()
        yield

    def test_get_sync_status_unauthenticated(self, client: TestClient):
        """Test getting sync status without authentication."""
        response = client.get("/sync/status")
        assert response.status_code == 401

    def test_get_sync_status(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting sync status."""
        response = authenticated_client.get("/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert "last_sync" in data
        assert "is_syncing" in data
        assert "indexed_files_count" in data
        assert "scheduler_running" in data

    def test_trigger_sync_now(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test triggering immediate sync."""
        with patch("routers.sync.sync_notes_to_vectors", new_callable=AsyncMock):
            response = authenticated_client.post("/sync/now")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sync_started"

    def test_trigger_sync_already_syncing(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test triggering sync when already syncing."""
        state = get_sync_state()
        state.is_syncing = True

        response = authenticated_client.post("/sync/now")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_syncing"

    def test_trigger_full_sync(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test triggering full sync."""
        with patch("routers.sync.sync_notes_to_vectors", new_callable=AsyncMock):
            response = authenticated_client.post("/sync/now?force_full=true")

        assert response.status_code == 200
        data = response.json()
        assert data["force_full"] is True

    def test_start_scheduler(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test starting sync scheduler."""
        response = authenticated_client.post(
            "/sync/scheduler/start",
            json={"enabled": True, "interval_minutes": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["interval_minutes"] == 10

    def test_stop_scheduler(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test stopping sync scheduler."""
        # First start it
        scheduler = get_scheduler()
        scheduler.start("test-token", 5)

        response = authenticated_client.post("/sync/scheduler/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    def test_get_indexed_files(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting list of indexed files."""
        state = get_sync_state()
        state.indexed_files = {
            "PersonalAI/Diary/2024-01-15.md": "2024-01-15T10:00:00Z",
            "PersonalAI/Projects/project.md": "2024-01-14T09:00:00Z",
        }

        response = authenticated_client.get("/sync/indexed-files")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["files"]) == 2


class TestSyncStatusDetails:
    """Tests for sync status details."""

    def test_status_includes_recent_errors(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test that status includes recent errors."""
        state = get_sync_state()
        state.errors = [
            "Error 1",
            "Error 2",
            "Error 3",
            "Error 4",
            "Error 5",
            "Error 6",  # More than 5
        ]

        response = authenticated_client.get("/sync/status")

        assert response.status_code == 200
        data = response.json()
        # Should only include last 5 errors
        assert len(data["recent_errors"]) == 5

    def test_status_shows_scheduler_running(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test that status shows scheduler state."""
        scheduler = get_scheduler()
        scheduler.start("test-token", 5)

        try:
            response = authenticated_client.get("/sync/status")

            assert response.status_code == 200
            data = response.json()
            assert data["scheduler_running"] is True
        finally:
            scheduler.stop()
