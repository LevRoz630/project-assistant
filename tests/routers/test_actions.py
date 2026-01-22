"""Tests for the actions router."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from services.actions import ActionStatus, ActionType, get_action_store


class TestActionsEndpoints:
    """Tests for actions endpoints."""

    @pytest.fixture(autouse=True)
    def clear_action_store(self):
        """Clear action store before each test."""
        store = get_action_store()
        store._actions.clear()
        yield
        store._actions.clear()

    def test_get_pending_actions_unauthenticated(self, client: TestClient):
        """Test getting pending actions without authentication."""
        response = client.get("/actions/pending")
        assert response.status_code == 401

    def test_get_pending_actions_empty(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting pending actions when empty."""
        response = authenticated_client.get("/actions/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["actions"] == []

    def test_get_pending_actions_with_data(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting pending actions with data."""
        store = get_action_store()
        store.create(
            ActionType.CREATE_TASK,
            {"title": "Test Task"},
            "User requested task creation",
        )

        response = authenticated_client.get("/actions/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["actions"][0]["type"] == "create_task"

    def test_create_action(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test creating a new action."""
        response = authenticated_client.post(
            "/actions/create",
            json={
                "type": "create_task",
                "data": {"title": "New Task", "body": "Description"},
                "reason": "AI suggested creating this task",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "create_task"
        assert data["status"] == "pending"
        assert data["data"]["title"] == "New Task"

    def test_get_action_by_id(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting action by ID."""
        store = get_action_store()
        action = store.create(
            ActionType.CREATE_EVENT,
            {"subject": "Meeting"},
            "Schedule meeting",
        )

        response = authenticated_client.get(f"/actions/{action.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == action.id
        assert data["type"] == "create_event"

    def test_get_action_not_found(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting non-existent action."""
        response = authenticated_client.get("/actions/nonexistent")

        assert response.status_code == 404

    def test_approve_action(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test approving an action."""
        store = get_action_store()
        action = store.create(
            ActionType.CREATE_TASK,
            {"title": "Task to approve"},
            "Reason",
        )

        with patch("routers.actions.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post(f"/actions/{action.id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "executed"

        # Verify action was updated
        updated = store.get(action.id)
        assert updated.status == ActionStatus.EXECUTED

    def test_approve_nonexistent_action(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test approving non-existent action."""
        response = authenticated_client.post("/actions/nonexistent/approve")

        assert response.status_code == 404

    def test_approve_non_pending_action(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test approving already processed action."""
        store = get_action_store()
        action = store.create(
            ActionType.CREATE_TASK,
            {"title": "Task"},
            "Reason",
        )
        store.update_status(action.id, ActionStatus.REJECTED)

        response = authenticated_client.post(f"/actions/{action.id}/approve")

        assert response.status_code == 400
        assert "not pending" in response.json()["detail"]

    def test_reject_action(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test rejecting an action."""
        store = get_action_store()
        action = store.create(
            ActionType.CREATE_EVENT,
            {"subject": "Meeting"},
            "Reason",
        )

        response = authenticated_client.post(f"/actions/{action.id}/reject")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

        # Verify action was updated
        updated = store.get(action.id)
        assert updated.status == ActionStatus.REJECTED

    def test_delete_action(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test deleting an action."""
        store = get_action_store()
        action = store.create(
            ActionType.CREATE_TASK,
            {"title": "Task"},
            "Reason",
        )

        response = authenticated_client.delete(f"/actions/{action.id}")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify action was deleted
        assert store.get(action.id) is None

    def test_get_action_history(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test getting action history."""
        store = get_action_store()

        # Create some actions with different statuses
        action1 = store.create(ActionType.CREATE_TASK, {"title": "1"}, "Reason")
        action2 = store.create(ActionType.CREATE_TASK, {"title": "2"}, "Reason")
        store.update_status(action1.id, ActionStatus.EXECUTED)
        store.update_status(action2.id, ActionStatus.REJECTED)

        response = authenticated_client.get("/actions/history")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2


class TestActionExecution:
    """Tests for action execution logic."""

    @pytest.fixture(autouse=True)
    def clear_action_store(self):
        """Clear action store before each test."""
        store = get_action_store()
        store._actions.clear()
        yield
        store._actions.clear()

    @pytest.mark.asyncio
    async def test_execute_create_task_action(self, mock_graph_client):
        """Test executing create task action."""
        from datetime import datetime

        from routers.actions import _execute_action
        from services.actions import ProposedAction

        action = ProposedAction(
            id="test-1",
            type=ActionType.CREATE_TASK,
            status=ActionStatus.PENDING,
            data={"title": "Test Task", "body": "Description"},
            reason="Test reason",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = await _execute_action(action, "test-token")

        assert "task_id" in result
        mock_graph_client.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_create_event_action(self, mock_graph_client):
        """Test executing create event action."""
        from datetime import datetime

        from routers.actions import _execute_action
        from services.actions import ProposedAction

        action = ProposedAction(
            id="test-2",
            type=ActionType.CREATE_EVENT,
            status=ActionStatus.PENDING,
            data={
                "subject": "Meeting",
                "start_datetime": "2024-01-20T10:00:00Z",
                "end_datetime": "2024-01-20T11:00:00Z",
            },
            reason="Test reason",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("routers.actions.GraphClient", return_value=mock_graph_client):
            result = await _execute_action(action, "test-token")

        assert "event_id" in result
        mock_graph_client.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_create_note_action(self, mock_graph_client):
        """Test executing create note action."""
        from datetime import datetime

        from routers.actions import _execute_action
        from services.actions import ProposedAction

        action = ProposedAction(
            id="test-3",
            type=ActionType.CREATE_NOTE,
            status=ActionStatus.PENDING,
            data={
                "folder": "Inbox",
                "filename": "new-note.md",
                "content": "# New Note\n\nContent here.",
            },
            reason="Test reason",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("routers.actions.GraphClient", return_value=mock_graph_client):
            with patch("routers.actions.ingest_document", new_callable=AsyncMock):
                result = await _execute_action(action, "test-token")

        assert "path" in result
        mock_graph_client.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_draft_email_action(self, mock_graph_client):
        """Test executing draft email action."""
        from datetime import datetime

        from routers.actions import _execute_action
        from services.actions import ProposedAction

        action = ProposedAction(
            id="test-4",
            type=ActionType.DRAFT_EMAIL,
            status=ActionStatus.PENDING,
            data={
                "to": ["recipient@test.com"],
                "subject": "Test Subject",
                "body": "Email body content.",
            },
            reason="Test reason",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("routers.actions.GraphClient", return_value=mock_graph_client):
            result = await _execute_action(action, "test-token")

        # Draft email saves as note
        assert "path" in result
        mock_graph_client.upload_file.assert_called_once()
