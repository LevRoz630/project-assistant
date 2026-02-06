"""Tests for Redis-backed services."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestChatHistory:
    """Tests for chat history Redis service."""

    @patch("backend.services.chat_history._get_redis")
    def test_get_chat_history_with_redis(self, mock_get_redis):
        """Test getting chat history from Redis."""
        from backend.services.chat_history import get_chat_history

        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps([
            {"id": "1", "title": "Test", "messages": [], "updatedAt": "2024-01-01T00:00:00"}
        ])
        mock_get_redis.return_value = mock_redis

        result = get_chat_history("test-session")

        assert len(result) == 1
        assert result[0]["id"] == "1"
        mock_redis.get.assert_called_once_with("chat_history:test-session")

    @patch("backend.services.chat_history._get_redis")
    def test_get_chat_history_no_redis(self, mock_get_redis):
        """Test getting chat history when Redis unavailable."""
        from backend.services.chat_history import get_chat_history

        mock_get_redis.return_value = None

        result = get_chat_history("test-session")

        assert result == []

    @patch("backend.services.chat_history._get_redis")
    def test_save_chat_history_limits_to_10(self, mock_get_redis):
        """Test that save_chat_history keeps only 10 most recent."""
        from backend.services.chat_history import save_chat_history, MAX_CONVERSATIONS

        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Create 15 conversations
        conversations = [
            {"id": str(i), "title": f"Conv {i}", "updatedAt": f"2024-01-{15-i:02d}T00:00:00"}
            for i in range(15)
        ]

        result = save_chat_history("test-session", conversations)

        assert result is True
        # Check that setex was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        assert len(saved_data) == MAX_CONVERSATIONS

    @patch("backend.services.chat_history._get_redis")
    def test_delete_conversation(self, mock_get_redis):
        """Test deleting a conversation."""
        from backend.services.chat_history import delete_conversation

        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps([
            {"id": "1", "title": "Test 1", "updatedAt": "2024-01-01T00:00:00"},
            {"id": "2", "title": "Test 2", "updatedAt": "2024-01-02T00:00:00"},
        ])
        mock_get_redis.return_value = mock_redis

        result = delete_conversation("test-session", "1")

        assert result is True
        # Verify the saved data doesn't contain the deleted conversation
        call_args = mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        assert len(saved_data) == 1
        assert saved_data[0]["id"] == "2"


class TestActionsStore:
    """Tests for actions Redis service."""

    @patch("backend.services.actions._get_redis")
    def test_create_action_saves_to_redis(self, mock_get_redis):
        """Test that creating an action saves to Redis."""
        from backend.services.actions import ActionStore, ActionType

        mock_redis = MagicMock()
        mock_redis.keys.return_value = []  # No existing actions
        mock_get_redis.return_value = mock_redis

        store = ActionStore()
        action = store.create(
            action_type=ActionType.CREATE_TASK,
            data={"title": "Test task"},
            reason="Testing",
        )

        assert action.id is not None
        mock_redis.setex.assert_called()

    @patch("backend.services.actions._get_redis")
    def test_update_status_saves_to_redis(self, mock_get_redis):
        """Test that updating action status saves to Redis."""
        from backend.services.actions import ActionStore, ActionType, ActionStatus

        mock_redis = MagicMock()
        mock_redis.keys.return_value = []
        mock_get_redis.return_value = mock_redis

        store = ActionStore()
        action = store.create(
            action_type=ActionType.CREATE_TASK,
            data={"title": "Test"},
            reason="Testing",
        )

        # Reset mock to track update call
        mock_redis.setex.reset_mock()

        store.update_status(action.id, ActionStatus.APPROVED)

        mock_redis.setex.assert_called()

    @patch("backend.services.actions._get_redis")
    def test_delete_action_removes_from_redis(self, mock_get_redis):
        """Test that deleting an action removes from Redis."""
        from backend.services.actions import ActionStore, ActionType

        mock_redis = MagicMock()
        mock_redis.keys.return_value = []
        mock_get_redis.return_value = mock_redis

        store = ActionStore()
        action = store.create(
            action_type=ActionType.CREATE_TASK,
            data={"title": "Test"},
            reason="Testing",
        )

        result = store.delete(action.id)

        assert result is True
        mock_redis.delete.assert_called_with(f"actions:{action.id}")


class TestSyncState:
    """Tests for sync state Redis service."""

    @patch("backend.services.sync._get_redis")
    def test_load_sync_state_from_redis(self, mock_get_redis):
        """Test loading sync state from Redis."""
        from backend.services.sync import _load_sync_state_from_redis

        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({
            "delta_link": "test-link",
            "last_sync": "2024-01-01T12:00:00",
            "indexed_files": {"path/to/file.md": "2024-01-01T10:00:00"},
        })
        mock_get_redis.return_value = mock_redis

        state = _load_sync_state_from_redis()

        assert state.delta_link == "test-link"
        assert state.last_sync is not None
        assert len(state.indexed_files) == 1

    @patch("backend.services.sync._get_redis")
    def test_save_sync_state_to_redis(self, mock_get_redis):
        """Test saving sync state to Redis."""
        from backend.services.sync import _save_sync_state_to_redis, SyncState

        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        state = SyncState(
            delta_link="test-link",
            last_sync=datetime(2024, 1, 1, 12, 0, 0),
            indexed_files={"test.md": "2024-01-01"},
        )

        _save_sync_state_to_redis(state)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "sync_state"

    @patch("backend.services.sync._get_redis")
    def test_sync_state_no_redis_returns_empty(self, mock_get_redis):
        """Test that missing Redis returns empty state."""
        from backend.services.sync import _load_sync_state_from_redis

        mock_get_redis.return_value = None

        state = _load_sync_state_from_redis()

        assert state.delta_link is None
        assert state.last_sync is None
        assert state.indexed_files == {}
