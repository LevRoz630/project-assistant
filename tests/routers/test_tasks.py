"""Tests for the tasks router."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


class TestTasksEndpoints:
    """Tests for tasks endpoints."""

    def test_get_task_lists_unauthenticated(self, client: TestClient):
        """Test getting task lists without authentication."""
        response = client.get("/tasks/lists")
        assert response.status_code == 401

    def test_get_task_lists(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting task lists."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/tasks/lists")

        assert response.status_code == 200
        data = response.json()
        assert "lists" in data
        assert len(data["lists"]) == 2

    def test_get_tasks_in_list(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting tasks in a specific list."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/tasks/list/list-1")

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data

    def test_get_tasks_include_completed(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting tasks including completed."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/tasks/list/list-1?include_completed=true")

        assert response.status_code == 200

    def test_get_all_tasks(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test getting all tasks from all lists."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.get("/tasks/all")

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data

    def test_create_task(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating a task."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post(
                "/tasks/create",
                json={
                    "list_id": "list-1",
                    "title": "New Task",
                    "body": "Task description",
                    "due_date": "2024-01-20T00:00:00Z",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "task" in data

    def test_create_task_minimal(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test creating a task with minimal data."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post(
                "/tasks/create",
                json={
                    "list_id": "list-1",
                    "title": "Simple Task",
                },
            )

        assert response.status_code == 200

    def test_complete_task(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test completing a task."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.post("/tasks/complete/list-1/task-1")

        assert response.status_code == 200
        mock_graph_client.complete_task.assert_called_once_with("list-1", "task-1")

    def test_delete_task(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test deleting a task."""
        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.delete("/tasks/delete/list-1/task-1")

        assert response.status_code == 200
        mock_graph_client.delete_task.assert_called_once_with("list-1", "task-1")

    def test_update_task(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
        mock_graph_client,
    ):
        """Test updating a task."""
        mock_graph_client.update_task = AsyncMock(
            return_value={
                "id": "task-1",
                "title": "Updated Task",
            }
        )

        with patch("routers.tasks.GraphClient", return_value=mock_graph_client):
            response = authenticated_client.patch(
                "/tasks/update/list-1/task-1",
                json={"title": "Updated Task"},
            )

        assert response.status_code == 200


class TestTasksValidation:
    """Tests for tasks input validation."""

    def test_create_task_missing_list_id(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test creating task without list_id."""
        response = authenticated_client.post(
            "/tasks/create",
            json={"title": "Task without list"},
        )

        assert response.status_code == 422

    def test_create_task_missing_title(
        self,
        authenticated_client: TestClient,
        mock_get_access_token,
    ):
        """Test creating task without title."""
        response = authenticated_client.post(
            "/tasks/create",
            json={"list_id": "list-1"},
        )

        assert response.status_code == 422
