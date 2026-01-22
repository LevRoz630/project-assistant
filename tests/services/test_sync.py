"""Tests for the sync service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.sync import (
    SyncScheduler,
    SyncState,
    get_scheduler,
    get_sync_state,
    sync_notes_to_vectors,
)


class TestSyncState:
    """Tests for SyncState class."""

    def test_default_state(self):
        """Test default sync state values."""
        state = SyncState()

        assert state.delta_link is None
        assert state.last_sync is None
        assert state.is_syncing is False
        assert state.indexed_files == {}
        assert state.errors == []

    def test_state_with_values(self):
        """Test sync state with custom values."""
        now = datetime.now()
        state = SyncState(
            delta_link="https://delta.link",
            last_sync=now,
            is_syncing=True,
            indexed_files={"path/to/file.md": "2024-01-15T10:00:00Z"},
            errors=["Error 1"],
        )

        assert state.delta_link == "https://delta.link"
        assert state.last_sync == now
        assert state.is_syncing is True
        assert len(state.indexed_files) == 1
        assert len(state.errors) == 1


class TestSyncScheduler:
    """Tests for SyncScheduler class."""

    def test_scheduler_initial_state(self):
        """Test scheduler initial state."""
        scheduler = SyncScheduler()

        assert scheduler.is_running is False
        assert scheduler._task is None
        assert scheduler._interval_minutes == 5

    def test_scheduler_start_stop(self):
        """Test starting and stopping scheduler."""
        scheduler = SyncScheduler()

        # Mock asyncio.create_task to avoid event loop requirement
        with patch("asyncio.create_task") as mock_create_task:
            mock_create_task.return_value = MagicMock()

            # Start scheduler
            scheduler.start("test-token", interval_minutes=10)
            assert scheduler.is_running is True
            assert scheduler._interval_minutes == 10
            assert scheduler._access_token == "test-token"
            mock_create_task.assert_called_once()

        # Stop scheduler
        scheduler.stop()
        assert scheduler.is_running is False

    def test_scheduler_update_token(self):
        """Test updating scheduler token."""
        scheduler = SyncScheduler()
        scheduler._access_token = "old-token"

        scheduler.update_token("new-token")
        assert scheduler._access_token == "new-token"


class TestSyncNotesToVectors:
    """Tests for sync_notes_to_vectors function."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create mock graph client for sync tests."""
        mock = MagicMock()
        mock.list_folder = AsyncMock(
            return_value={
                "value": [
                    {"name": "Diary", "folder": {}},
                    {"name": "Projects", "folder": {}},
                ]
            }
        )
        mock.get_file_content = AsyncMock(return_value=b"# Test Content")
        return mock

    @pytest.mark.asyncio
    async def test_sync_returns_already_syncing(self):
        """Test sync returns early when already syncing."""
        state = get_sync_state()
        original_syncing = state.is_syncing
        state.is_syncing = True

        try:
            result = await sync_notes_to_vectors("test-token")
            assert result["status"] == "already_syncing"
        finally:
            state.is_syncing = original_syncing

    @pytest.mark.asyncio
    async def test_sync_full_sync(self, mock_graph_client):
        """Test full sync execution."""
        state = get_sync_state()
        state.is_syncing = False
        state.delta_link = None

        with patch("services.sync.GraphClient", return_value=mock_graph_client):
            with patch("services.sync.ingest_document", new_callable=AsyncMock):
                # Mock nested folder listing
                mock_graph_client.list_folder = AsyncMock(
                    side_effect=[
                        # First call - list base folders
                        {"value": [{"name": "Diary", "folder": {}}]},
                        # Second call - list Diary contents
                        {
                            "value": [
                                {
                                    "name": "2024-01-15.md",
                                    "file": {},
                                    "lastModifiedDateTime": "2024-01-15T10:00:00Z",
                                }
                            ]
                        },
                    ]
                )

                result = await sync_notes_to_vectors("test-token", force_full=True)

                assert result["status"] == "completed"
                assert "stats" in result
                assert state.last_sync is not None


class TestGlobalSyncState:
    """Tests for global sync state singleton."""

    def test_get_sync_state_returns_singleton(self):
        """Test that get_sync_state returns the same instance."""
        state1 = get_sync_state()
        state2 = get_sync_state()
        assert state1 is state2

    def test_get_scheduler_returns_singleton(self):
        """Test that get_scheduler returns the same instance."""
        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()
        assert scheduler1 is scheduler2
