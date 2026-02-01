"""Microsoft To Do tasks endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_access_token_for_service
from ..services.context_cache import invalidate_context
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
    request: Request,
    include_completed: bool = False,
    include_flagged_emails: bool = True,
    client: GraphClient = Depends(get_graph_client),
):
    """List all important (high priority) tasks and flagged emails."""
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
                            "type": "task",
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

        # Fetch flagged emails if requested
        flagged_emails = []
        if include_flagged_emails:
            session_id = request.cookies.get("session_id")
            email_token = get_access_token_for_service(session_id, "email") if session_id else None
            if email_token:
                try:
                    email_client = GraphClient(email_token)
                    emails_result = await email_client.list_flagged_emails(top=20)
                    for email in emails_result.get("value", []):
                        from_info = email.get("from", {}).get("emailAddress", {})
                        flagged_emails.append(
                            {
                                "id": email["id"],
                                "type": "email",
                                "title": email.get("subject", "(No subject)"),
                                "body": email.get("bodyPreview", "")[:200],
                                "from_name": from_info.get("name", "Unknown"),
                                "from_email": from_info.get("address", ""),
                                "created": email.get("receivedDateTime"),
                                "is_read": email.get("isRead", False),
                                "importance": "flagged",
                            }
                        )
                except Exception:
                    # Don't fail the whole request if email fetch fails
                    pass

        # Combine and sort by date
        all_items = important_tasks + flagged_emails
        all_items.sort(key=lambda x: (x.get("due_date") or x.get("created") or "9999"))

        return {
            "items": all_items,
            "tasks": important_tasks,
            "flagged_emails": flagged_emails,
            "count": len(all_items),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/create")
async def create_task(
    request: Request,
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

        # Invalidate tasks cache so next chat message gets fresh data
        session_id = request.cookies.get("session_id")
        if session_id:
            invalidate_context("tasks", session_id)

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
    request: Request,
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

        # Invalidate tasks cache so next chat message gets fresh data
        session_id = request.cookies.get("session_id")
        if session_id:
            invalidate_context("tasks", session_id)

        return {"success": True, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/complete/{list_id}/{task_id}")
async def complete_task(
    request: Request,
    list_id: str,
    task_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Mark a task as complete."""
    try:
        await client.complete_task(list_id, task_id)

        # Invalidate tasks cache so next chat message gets fresh data
        session_id = request.cookies.get("session_id")
        if session_id:
            invalidate_context("tasks", session_id)

        return {"success": True, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/delete/{list_id}/{task_id}")
async def delete_task(
    request: Request,
    list_id: str,
    task_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Delete a task."""
    try:
        await client.delete_task(list_id, task_id)

        # Invalidate tasks cache so next chat message gets fresh data
        session_id = request.cookies.get("session_id")
        if session_id:
            invalidate_context("tasks", session_id)

        return {"success": True, "deleted": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
