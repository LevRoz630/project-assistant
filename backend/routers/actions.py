"""Actions router for managing AI-proposed actions."""

import json
from datetime import datetime

from ..auth import get_access_token
from ..config import get_settings
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..services.actions import (
    ActionStatus,
    ActionType,
    EmailDraftAction,
    EventAction,
    MoveNoteAction,
    NoteAction,
    ProposedAction,
    TaskAction,
    TaskUpdateAction,
    get_action_store,
)
from ..services.graph import GraphClient
from ..services.vectors import delete_document, ingest_document

router = APIRouter(prefix="/actions", tags=["actions"])
settings = get_settings()

ACTIONS_FILE_PATH = "_system/pending_actions.json"


async def _load_actions_from_cloud(token: str) -> list[dict]:
    """Load actions from OneDrive."""
    client = GraphClient(token)
    file_path = f"{settings.onedrive_base_folder}/{ACTIONS_FILE_PATH}"

    try:
        content = await client.get_file_content(file_path)
        data = json.loads(content.decode("utf-8"))
        return data.get("actions", [])
    except Exception:
        return []


async def _save_actions_to_cloud(token: str, actions: list[dict]):
    """Save actions to OneDrive."""
    client = GraphClient(token)
    file_path = f"{settings.onedrive_base_folder}/{ACTIONS_FILE_PATH}"

    content = json.dumps({"actions": actions, "updated_at": datetime.now().isoformat()}, indent=2)
    try:
        await client.upload_file(file_path, content.encode("utf-8"))
    except Exception:
        pass  # Don't fail if we can't save to cloud


async def _sync_actions_from_cloud(token: str):
    """Sync in-memory actions with OneDrive."""
    store = get_action_store()
    cloud_actions = await _load_actions_from_cloud(token)

    for action_data in cloud_actions:
        if not store.get(action_data["id"]):
            # Reconstruct the action from stored data
            action = ProposedAction(
                id=action_data["id"],
                type=ActionType(action_data["type"]),
                status=ActionStatus(action_data["status"]),
                data=action_data["data"],
                reason=action_data["reason"],
                created_at=datetime.fromisoformat(action_data["created_at"]),
                updated_at=datetime.fromisoformat(action_data["updated_at"]),
                error=action_data.get("error"),
            )
            store._actions[action.id] = action


async def _persist_actions_to_cloud(token: str):
    """Persist current actions to OneDrive."""
    store = get_action_store()
    actions_data = []

    for action in store._actions.values():
        actions_data.append({
            "id": action.id,
            "type": action.type.value,
            "status": action.status.value,
            "data": action.data,
            "reason": action.reason,
            "created_at": action.created_at.isoformat(),
            "updated_at": action.updated_at.isoformat(),
            "error": action.error,
        })

    await _save_actions_to_cloud(token, actions_data)


class CreateActionRequest(BaseModel):
    """Request to create a proposed action."""

    type: ActionType
    data: dict
    reason: str

    def validate_data(self) -> dict:
        """Validate data against the appropriate schema for the action type."""
        schema_map = {
            ActionType.CREATE_TASK: TaskAction,
            ActionType.UPDATE_TASK: TaskUpdateAction,
            ActionType.CREATE_EVENT: EventAction,
            ActionType.CREATE_NOTE: NoteAction,
            ActionType.EDIT_NOTE: NoteAction,
            ActionType.MOVE_NOTE: MoveNoteAction,
            ActionType.DRAFT_EMAIL: EmailDraftAction,
        }

        schema = schema_map.get(self.type)
        if schema:
            # This will raise ValidationError if data doesn't match schema
            validated = schema(**self.data)
            return validated.model_dump()
        return self.data


class ActionResponse(BaseModel):
    """Response for action operations."""

    id: str
    type: str
    status: str
    data: dict
    reason: str
    created_at: str
    error: str | None = None


def _action_to_response(action: ProposedAction) -> dict:
    """Convert ProposedAction to response dict."""
    return {
        "id": action.id,
        "type": action.type.value,
        "status": action.status.value,
        "data": action.data,
        "reason": action.reason,
        "created_at": action.created_at.isoformat(),
        "error": action.error,
    }


@router.get("/pending")
async def get_pending_actions(request: Request):
    """Get all pending actions awaiting approval."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if token:
        await _sync_actions_from_cloud(token)

    store = get_action_store()

    # Clean up old non-pending actions to prevent memory buildup
    store.clear_old(hours=48)

    actions = store.list_pending()

    return {
        "count": len(actions),
        "actions": [_action_to_response(a) for a in actions],
    }


@router.get("/history")
async def get_action_history(request: Request, limit: int = 50):
    """Get action history."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    store = get_action_store()
    actions = store.list_all(limit)

    return {
        "count": len(actions),
        "actions": [_action_to_response(a) for a in actions],
    }


@router.get("/{action_id}")
async def get_action(request: Request, action_id: str):
    """Get a specific action."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    store = get_action_store()
    action = store.get(action_id)

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    return _action_to_response(action)


@router.post("/create")
async def create_action(request: Request, action_request: CreateActionRequest):
    """Create a new proposed action."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate the action data against the appropriate schema
    try:
        validated_data = action_request.validate_data()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid action data: {e}") from e

    token = get_access_token(session_id)
    store = get_action_store()

    action = store.create(
        action_type=action_request.type,
        data=validated_data,
        reason=action_request.reason,
    )

    # Persist to OneDrive
    if token:
        await _persist_actions_to_cloud(token)

    return _action_to_response(action)


@router.post("/{action_id}/approve")
async def approve_action(request: Request, action_id: str):
    """Approve and execute an action."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    store = get_action_store()
    action = store.get(action_id)

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.status != ActionStatus.PENDING:
        raise HTTPException(
            status_code=400, detail=f"Action is not pending (status: {action.status.value})"
        )

    # Execute the action
    try:
        result = await _execute_action(action, token)
        store.update_status(action_id, ActionStatus.EXECUTED)
        await _persist_actions_to_cloud(token)
        return {
            "status": "executed",
            "action": _action_to_response(action),
            "result": result,
        }
    except Exception as e:
        store.update_status(action_id, ActionStatus.FAILED, str(e))
        await _persist_actions_to_cloud(token)
        raise HTTPException(status_code=500, detail=f"Action execution failed: {e}") from e


@router.post("/{action_id}/reject")
async def reject_action(request: Request, action_id: str):
    """Reject an action."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    store = get_action_store()
    action = store.get(action_id)

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.status != ActionStatus.PENDING:
        raise HTTPException(
            status_code=400, detail=f"Action is not pending (status: {action.status.value})"
        )

    store.update_status(action_id, ActionStatus.REJECTED)
    await _persist_actions_to_cloud(token)

    return {
        "status": "rejected",
        "action": _action_to_response(action),
    }


@router.delete("/{action_id}")
async def delete_action(request: Request, action_id: str):
    """Delete an action from history."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    store = get_action_store()

    if store.delete(action_id):
        if token:
            await _persist_actions_to_cloud(token)
        return {"status": "deleted", "id": action_id}
    else:
        raise HTTPException(status_code=404, detail="Action not found")


async def _execute_action(action: ProposedAction, token: str) -> dict:
    """Execute an approved action."""
    client = GraphClient(token)

    if action.type == ActionType.CREATE_TASK:
        data = action.data
        list_id = data.get("list_id")

        # If no list specified, get the default task list
        if not list_id:
            lists_result = await client.list_task_lists()
            lists = lists_result.get("value", [])
            if lists:
                # Use "Tasks" list or first available
                default_list = next(
                    (tl for tl in lists if tl.get("displayName") == "Tasks"), lists[0]
                )
                list_id = default_list.get("id")

        if not list_id:
            raise Exception("No task list available")

        result = await client.create_task(
            list_id=list_id,
            title=data.get("title", "Untitled Task"),
            body=data.get("body"),
            due_date=data.get("due_date"),
        )

        return {"task_id": result.get("id"), "title": result.get("title")}

    elif action.type == ActionType.UPDATE_TASK:
        data = action.data
        list_id = data.get("list_id")
        task_id = data.get("task_id")

        if not list_id or not task_id:
            raise Exception("list_id and task_id are required for updating a task")

        updates = {}
        if data.get("title"):
            updates["title"] = data["title"]
        if data.get("body") is not None:
            updates["body"] = {"content": data["body"], "contentType": "text"}
        if data.get("due_date"):
            updates["dueDateTime"] = {"dateTime": data["due_date"], "timeZone": "UTC"}
        if data.get("status"):
            updates["status"] = data["status"]
        if data.get("importance"):
            updates["importance"] = data["importance"]

        if not updates:
            raise Exception("No updates provided")

        await client.update_task(list_id, task_id, updates)

        return {"task_id": task_id, "updated_fields": list(updates.keys())}

    elif action.type == ActionType.CREATE_EVENT:
        data = action.data

        result = await client.create_event(
            subject=data.get("subject", "Untitled Event"),
            start_datetime=data.get("start_datetime"),
            end_datetime=data.get("end_datetime"),
            body=data.get("body"),
            location=data.get("location"),
            attendees=data.get("attendees"),
        )

        return {"event_id": result.get("id"), "subject": result.get("subject")}

    elif action.type == ActionType.CREATE_NOTE:
        data = action.data
        folder = data.get("folder", "Inbox")
        filename = data.get("filename", "untitled.md")
        content = data.get("content", "")

        file_path = f"{settings.onedrive_base_folder}/{folder}/{filename}"
        result = await client.upload_file(file_path, content.encode("utf-8"))

        # Also index the new note
        indexed = False
        try:
            await ingest_document(
                content=content,
                source_path=file_path,
                metadata={"folder": folder, "filename": filename},
            )
            indexed = True
        except Exception:
            pass  # Indexing failure is non-critical

        return {"path": file_path, "name": result.get("name"), "indexed": indexed}

    elif action.type == ActionType.EDIT_NOTE:
        data = action.data
        folder = data.get("folder")
        filename = data.get("filename")
        content = data.get("content", "")

        if not folder or not filename:
            raise Exception("folder and filename are required for editing a note")

        file_path = f"{settings.onedrive_base_folder}/{folder}/{filename}"

        # Check if note exists before editing
        try:
            await client.get_item_by_path(file_path)
        except Exception as e:
            if "itemNotFound" in str(e).lower() or "not found" in str(e).lower():
                raise Exception(f"Note '{filename}' not found in folder '{folder}'") from e
            raise

        result = await client.upload_file(file_path, content.encode("utf-8"))

        # Re-index the edited note
        indexed = False
        try:
            await ingest_document(
                content=content,
                source_path=file_path,
                metadata={"folder": folder, "filename": filename},
            )
            indexed = True
        except Exception:
            pass  # Indexing failure is non-critical

        return {"path": file_path, "name": result.get("name"), "indexed": indexed}

    elif action.type == ActionType.MOVE_NOTE:
        data = action.data
        filename = data.get("filename")
        source_folder = data.get("source_folder")
        target_folder = data.get("target_folder")

        if not filename or not source_folder or not target_folder:
            raise Exception("filename, source_folder, and target_folder are required")

        source_path = f"{settings.onedrive_base_folder}/{source_folder}/{filename}"
        target_folder_path = f"{settings.onedrive_base_folder}/{target_folder}"

        # Move file
        result = await client.move_item(source_path, target_folder_path, filename)

        # Update vector store
        new_path = f"{settings.onedrive_base_folder}/{target_folder}/{filename}"
        try:
            await delete_document(source_path)
            content = await client.get_file_content(new_path)
            await ingest_document(
                content=content.decode("utf-8"),
                source_path=new_path,
                metadata={"folder": target_folder, "filename": filename},
            )
        except Exception:
            pass  # Vector store update is non-critical

        return {"moved": True, "new_folder": target_folder, "new_path": new_path}

    elif action.type == ActionType.DRAFT_EMAIL:
        # For email drafts, we just save it as a note for now
        # Full email sending would require additional Graph API permissions
        data = action.data
        to = ", ".join(data.get("to", []))
        subject = data.get("subject", "")
        body = data.get("body", "")

        draft_content = f"""# Email Draft

**To:** {to}
**Subject:** {subject}

---

{body}

---
*Created by Project Assistant. Review before sending.*
"""

        filename = f"draft-{action.id}.md"
        file_path = f"{settings.onedrive_base_folder}/Inbox/{filename}"
        result = await client.upload_file(file_path, draft_content.encode("utf-8"))

        return {"path": file_path, "note": "Email saved as draft note"}

    else:
        raise Exception(f"Unknown action type: {action.type}")
