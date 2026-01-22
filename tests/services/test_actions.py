"""Tests for the actions service."""

from datetime import datetime

import pytest
from services.actions import (
    ActionStatus,
    ActionStore,
    ActionType,
    ProposedAction,
    format_action_for_chat,
    get_action_store,
)


class TestActionStore:
    """Tests for ActionStore class."""

    @pytest.fixture
    def store(self) -> ActionStore:
        """Create a fresh ActionStore for each test."""
        return ActionStore()

    def test_create_action(self, store: ActionStore):
        """Test creating a new action."""
        action = store.create(
            action_type=ActionType.CREATE_TASK,
            data={"title": "Test Task", "body": "Description"},
            reason="User asked to create a task",
        )

        assert action.id is not None
        assert len(action.id) == 8
        assert action.type == ActionType.CREATE_TASK
        assert action.status == ActionStatus.PENDING
        assert action.data["title"] == "Test Task"
        assert action.reason == "User asked to create a task"
        assert isinstance(action.created_at, datetime)
        assert isinstance(action.updated_at, datetime)

    def test_get_action(self, store: ActionStore):
        """Test retrieving an action by ID."""
        created = store.create(
            action_type=ActionType.CREATE_EVENT,
            data={"subject": "Meeting"},
            reason="Schedule a meeting",
        )

        retrieved = store.get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.type == ActionType.CREATE_EVENT

    def test_get_nonexistent_action(self, store: ActionStore):
        """Test retrieving a non-existent action."""
        result = store.get("nonexistent-id")
        assert result is None

    def test_list_pending(self, store: ActionStore):
        """Test listing pending actions."""
        # Create multiple actions
        store.create(ActionType.CREATE_TASK, {"title": "Task 1"}, "Reason 1")
        action2 = store.create(ActionType.CREATE_TASK, {"title": "Task 2"}, "Reason 2")
        store.create(ActionType.CREATE_EVENT, {"subject": "Event"}, "Reason 3")

        # Mark one as approved
        store.update_status(action2.id, ActionStatus.APPROVED)

        pending = store.list_pending()
        assert len(pending) == 2
        assert all(a.status == ActionStatus.PENDING for a in pending)

    def test_list_all(self, store: ActionStore):
        """Test listing all actions."""
        for i in range(5):
            store.create(ActionType.CREATE_TASK, {"title": f"Task {i}"}, f"Reason {i}")

        all_actions = store.list_all(limit=3)
        assert len(all_actions) == 3

    def test_update_status(self, store: ActionStore):
        """Test updating action status."""
        action = store.create(ActionType.CREATE_TASK, {"title": "Task"}, "Reason")
        original_updated = action.updated_at

        # Small delay to ensure timestamp changes
        updated = store.update_status(action.id, ActionStatus.EXECUTED)

        assert updated is not None
        assert updated.status == ActionStatus.EXECUTED
        assert updated.updated_at >= original_updated

    def test_update_status_with_error(self, store: ActionStore):
        """Test updating action status with error message."""
        action = store.create(ActionType.CREATE_TASK, {"title": "Task"}, "Reason")

        store.update_status(action.id, ActionStatus.FAILED, "Something went wrong")

        updated = store.get(action.id)
        assert updated is not None
        assert updated.status == ActionStatus.FAILED
        assert updated.error == "Something went wrong"

    def test_delete_action(self, store: ActionStore):
        """Test deleting an action."""
        action = store.create(ActionType.CREATE_TASK, {"title": "Task"}, "Reason")

        result = store.delete(action.id)
        assert result is True
        assert store.get(action.id) is None

    def test_delete_nonexistent_action(self, store: ActionStore):
        """Test deleting a non-existent action."""
        result = store.delete("nonexistent-id")
        assert result is False

    def test_clear_old_actions(self, store: ActionStore):
        """Test clearing old actions."""
        # Create some actions
        action1 = store.create(ActionType.CREATE_TASK, {"title": "Task 1"}, "Reason")
        action2 = store.create(ActionType.CREATE_TASK, {"title": "Task 2"}, "Reason")

        # Mark one as completed
        store.update_status(action1.id, ActionStatus.EXECUTED)

        # Clear old (won't clear recent ones)
        store.clear_old(hours=0)

        # Both should still exist since they're very recent
        assert store.get(action1.id) is not None
        assert store.get(action2.id) is not None


class TestActionTypes:
    """Tests for action type enums."""

    def test_action_type_values(self):
        """Test ActionType enum values."""
        assert ActionType.CREATE_TASK.value == "create_task"
        assert ActionType.CREATE_EVENT.value == "create_event"
        assert ActionType.CREATE_NOTE.value == "create_note"
        assert ActionType.EDIT_NOTE.value == "edit_note"
        assert ActionType.DRAFT_EMAIL.value == "draft_email"

    def test_action_status_values(self):
        """Test ActionStatus enum values."""
        assert ActionStatus.PENDING.value == "pending"
        assert ActionStatus.APPROVED.value == "approved"
        assert ActionStatus.REJECTED.value == "rejected"
        assert ActionStatus.EXECUTED.value == "executed"
        assert ActionStatus.FAILED.value == "failed"


class TestFormatActionForChat:
    """Tests for format_action_for_chat function."""

    def test_format_task_action(self):
        """Test formatting a task action for chat."""
        action = ProposedAction(
            id="abc123",
            type=ActionType.CREATE_TASK,
            status=ActionStatus.PENDING,
            data={
                "title": "Buy groceries",
                "body": "Milk, eggs, bread",
                "due_date": "2024-01-20",
                "importance": "high",
            },
            reason="User mentioned they need to buy groceries",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        formatted = format_action_for_chat(action)

        assert "abc123" in formatted
        assert "create_task" in formatted
        assert "Buy groceries" in formatted
        assert "Milk, eggs, bread" in formatted
        assert "2024-01-20" in formatted
        assert "high" in formatted
        assert "approve abc123" in formatted
        assert "reject abc123" in formatted

    def test_format_event_action(self):
        """Test formatting an event action for chat."""
        action = ProposedAction(
            id="xyz789",
            type=ActionType.CREATE_EVENT,
            status=ActionStatus.PENDING,
            data={
                "subject": "Team Meeting",
                "start_datetime": "2024-01-20T10:00:00",
                "end_datetime": "2024-01-20T11:00:00",
                "location": "Room 101",
                "attendees": ["alice@test.com", "bob@test.com"],
            },
            reason="Schedule team sync",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        formatted = format_action_for_chat(action)

        assert "xyz789" in formatted
        assert "create_event" in formatted
        assert "Team Meeting" in formatted
        assert "Room 101" in formatted
        assert "alice@test.com" in formatted

    def test_format_email_draft_action(self):
        """Test formatting an email draft action for chat."""
        action = ProposedAction(
            id="email01",
            type=ActionType.DRAFT_EMAIL,
            status=ActionStatus.PENDING,
            data={
                "to": ["recipient@test.com"],
                "subject": "Follow up",
                "body": "Thank you for the meeting.",
            },
            reason="Draft follow-up email",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        formatted = format_action_for_chat(action)

        assert "email01" in formatted
        assert "draft_email" in formatted
        assert "recipient@test.com" in formatted
        assert "Follow up" in formatted
        assert "Thank you for the meeting" in formatted


class TestGlobalActionStore:
    """Tests for global action store singleton."""

    def test_get_action_store_returns_singleton(self):
        """Test that get_action_store returns the same instance."""
        store1 = get_action_store()
        store2 = get_action_store()
        assert store1 is store2
