"""Microsoft To Do tasks endpoints."""

from ..auth import get_access_token_for_service
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from ..services.graph import GraphClient

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_graph_client(request: Request) -> GraphClient:
    """Dependency to get authenticated Graph client for tasks."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token_for_service(session_id, "tasks")
    if not token:
        raise HTTPException(
            status_code=401, detail="Session expired or no tasks account configured"
        )

    return GraphClient(token)


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    title: str
    body: str | None = None
    due_date: str | None = None  # ISO format: 2026-01-21T10:00:00
    list_id: str | None = None  # If not provided, uses default list


class TaskUpdate(BaseModel):
    """Request body for updating a task."""

    title: str | None = None
    body: str | None = None
    due_date: str | None = None
    status: str | None = None  # "notStarted", "inProgress", "completed"


@router.get("/lists")
async def list_task_lists(client: GraphClient = Depends(get_graph_client)):
    """List all task lists."""
    try:
        result = await client.list_task_lists()
        lists = [
            {
                "id": item["id"],
                "name": item["displayName"],
                "is_default": item.get("wellknownListName") == "defaultList",
            }
            for item in result.get("value", [])
        ]
        return {"lists": lists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list/{list_id}")
async def list_tasks(
    list_id: str,
    include_completed: bool = False,
    client: GraphClient = Depends(get_graph_client),
):
    """List tasks in a specific list."""
    try:
        result = await client.list_tasks(list_id, include_completed)
        tasks = [
            {
                "id": task["id"],
                "title": task["title"],
                "body": task.get("body", {}).get("content", ""),
                "status": task["status"],
                "due_date": task.get("dueDateTime", {}).get("dateTime"),
                "created": task.get("createdDateTime"),
                "completed": task.get("completedDateTime", {}).get("dateTime"),
                "importance": task.get("importance", "normal"),
            }
            for task in result.get("value", [])
        ]

        # Sort by due date, then by creation
        tasks.sort(key=lambda x: (x.get("due_date") or "9999", x.get("created") or ""))

        return {"list_id": list_id, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/all")
async def list_all_tasks(
    include_completed: bool = False,
    client: GraphClient = Depends(get_graph_client),
):
    """List tasks from all lists."""
    try:
        lists_result = await client.list_task_lists()
        all_tasks = []

        for task_list in lists_result.get("value", []):
            list_id = task_list["id"]
            list_name = task_list["displayName"]

            tasks_result = await client.list_tasks(list_id, include_completed)
            for task in tasks_result.get("value", []):
                all_tasks.append(
                    {
                        "id": task["id"],
                        "list_id": list_id,
                        "list_name": list_name,
                        "title": task["title"],
                        "body": task.get("body", {}).get("content", ""),
                        "status": task["status"],
                        "due_date": task.get("dueDateTime", {}).get("dateTime"),
                        "created": task.get("createdDateTime"),
                        "importance": task.get("importance", "normal"),
                    }
                )

        # Sort by due date
        all_tasks.sort(key=lambda x: (x.get("due_date") or "9999", x.get("created") or ""))

        return {"tasks": all_tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/important")
async def list_important_tasks(
    include_completed: bool = False,
    client: GraphClient = Depends(get_graph_client),
):
    """List all important (high priority) tasks from all lists."""
    try:
        lists_result = await client.list_task_lists()
        important_tasks = []

        for task_list in lists_result.get("value", []):
            list_id = task_list["id"]
            list_name = task_list["displayName"]

            tasks_result = await client.list_tasks(list_id, include_completed)
            for task in tasks_result.get("value", []):
                if task.get("importance") == "high":
                    important_tasks.append(
                        {
                            "id": task["id"],
                            "list_id": list_id,
                            "list_name": list_name,
                            "title": task["title"],
                            "body": task.get("body", {}).get("content", ""),
                            "status": task["status"],
                            "due_date": task.get("dueDateTime", {}).get("dateTime"),
                            "created": task.get("createdDateTime"),
                            "importance": "high",
                        }
                    )

        # Sort by due date
        important_tasks.sort(key=lambda x: (x.get("due_date") or "9999", x.get("created") or ""))

        return {"tasks": important_tasks, "count": len(important_tasks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/create")
async def create_task(
    task: TaskCreate,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a new task."""
    try:
        # Get default list if not specified
        list_id = task.list_id
        if not list_id:
            lists_result = await client.list_task_lists()
            for task_list in lists_result.get("value", []):
                if task_list.get("wellknownListName") == "defaultList":
                    list_id = task_list["id"]
                    break

            if not list_id and lists_result.get("value"):
                list_id = lists_result["value"][0]["id"]

        if not list_id:
            raise HTTPException(status_code=400, detail="No task list found")

        result = await client.create_task(
            list_id=list_id,
            title=task.title,
            body=task.body,
            due_date=task.due_date,
        )

        return {
            "success": True,
            "task": {
                "id": result["id"],
                "title": result["title"],
                "list_id": list_id,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/update/{list_id}/{task_id}")
async def update_task(
    list_id: str,
    task_id: str,
    task: TaskUpdate,
    client: GraphClient = Depends(get_graph_client),
):
    """Update a task."""
    try:
        updates = {}
        if task.title is not None:
            updates["title"] = task.title
        if task.body is not None:
            updates["body"] = {"content": task.body, "contentType": "text"}
        if task.due_date is not None:
            updates["dueDateTime"] = {"dateTime": task.due_date, "timeZone": "UTC"}
        if task.status is not None:
            updates["status"] = task.status

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        await client.update_task(list_id, task_id, updates)

        return {"success": True, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/complete/{list_id}/{task_id}")
async def complete_task(
    list_id: str,
    task_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Mark a task as complete."""
    try:
        await client.complete_task(list_id, task_id)
        return {"success": True, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/delete/{list_id}/{task_id}")
async def delete_task(
    list_id: str,
    task_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Delete a task."""
    try:
        await client.delete_task(list_id, task_id)
        return {"success": True, "deleted": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
