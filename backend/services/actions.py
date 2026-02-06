"""AI Actions service for managing proposed actions that require approval."""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from ..auth import _get_redis

logger = logging.getLogger(__name__)

# Redis configuration
ACTIONS_KEY_PREFIX = "actions:"
ACTIONS_TTL = 60 * 60 * 24 * 7  # 7 days


class ActionType(str, Enum):
    """Types of actions the AI can propose."""

    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    CREATE_EVENT = "create_event"
    CREATE_NOTE = "create_note"
    EDIT_NOTE = "edit_note"
    MOVE_NOTE = "move_note"
    DRAFT_EMAIL = "draft_email"


class ActionStatus(str, Enum):
    """Status of a proposed action."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class TaskAction(BaseModel):
    """Data for creating a task."""

    title: str
    body: str | None = None
    due_date: str | None = None
    list_id: str | None = None
    importance: str = "normal"


class TaskUpdateAction(BaseModel):
    """Data for updating an existing task."""

    task_id: str
    list_id: str
    title: str | None = None
    body: str | None = None
    due_date: str | None = None
    status: str | None = None  # "notStarted", "inProgress", "completed"
    importance: str | None = None  # "low", "normal", "high"


class EventAction(BaseModel):
    """Data for creating a calendar event."""

    subject: str
    start_datetime: str
    end_datetime: str
    body: str | None = None
    location: str | None = None
    attendees: list[str] | None = None


class NoteAction(BaseModel):
    """Data for creating or editing a note."""

    folder: str
    filename: str
    content: str
    original_content: str | None = None  # For edits, to show diff


class MoveNoteAction(BaseModel):
    """Data for moving a note to a different folder."""

    filename: str
    source_folder: str
    target_folder: str


class EmailDraftAction(BaseModel):
    """Data for drafting an email reply."""

    to: list[str]
    subject: str
    body: str
    reply_to_id: str | None = None  # Original email ID if this is a reply


@dataclass
class ProposedAction:
    """A proposed action awaiting user approval."""

    id: str
    type: ActionType
    status: ActionStatus
    data: dict
    reason: str  # Why the AI is proposing this action
    created_at: datetime
    updated_at: datetime
    error: str | None = None


def _action_to_dict(action: ProposedAction) -> dict:
    """Serialize ProposedAction to dict for JSON storage."""
    return {
        "id": action.id,
        "type": action.type.value,
        "status": action.status.value,
        "data": action.data,
        "reason": action.reason,
        "created_at": action.created_at.isoformat(),
        "updated_at": action.updated_at.isoformat(),
        "error": action.error,
    }


def _dict_to_action(d: dict) -> ProposedAction:
    """Deserialize dict to ProposedAction."""
    return ProposedAction(
        id=d["id"],
        type=ActionType(d["type"]),
        status=ActionStatus(d["status"]),
        data=d["data"],
        reason=d["reason"],
        created_at=datetime.fromisoformat(d["created_at"]),
        updated_at=datetime.fromisoformat(d["updated_at"]),
        error=d.get("error"),
    )


class ActionStore:
    """Redis-backed store for proposed actions with memory fallback."""

    def __init__(self):
        self._actions: dict[str, ProposedAction] = {}
        self._load_from_redis()

    def _load_from_redis(self):
        """Load actions from Redis on startup."""
        redis = _get_redis()
        if not redis:
            return

        try:
            # Get all action keys
            keys = redis.keys(f"{ACTIONS_KEY_PREFIX}*")
            for key in keys:
                data = redis.get(key)
                if data:
                    action_dict = json.loads(data)
                    action = _dict_to_action(action_dict)
                    self._actions[action.id] = action
            if keys:
                logger.info(f"Loaded {len(keys)} actions from Redis")
        except Exception as e:
            logger.warning(f"Failed to load actions from Redis: {e}")

    def _save_to_redis(self, action: ProposedAction):
        """Save a single action to Redis."""
        redis = _get_redis()
        if not redis:
            return

        try:
            key = f"{ACTIONS_KEY_PREFIX}{action.id}"
            redis.setex(key, ACTIONS_TTL, json.dumps(_action_to_dict(action)))
        except Exception as e:
            logger.warning(f"Failed to save action to Redis: {e}")

    def _delete_from_redis(self, action_id: str):
        """Delete an action from Redis."""
        redis = _get_redis()
        if not redis:
            return

        try:
            redis.delete(f"{ACTIONS_KEY_PREFIX}{action_id}")
        except Exception as e:
            logger.warning(f"Failed to delete action from Redis: {e}")

    def create(
        self,
        action_type: ActionType,
        data: dict,
        reason: str,
    ) -> ProposedAction:
        """Create a new proposed action."""
        action_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        action = ProposedAction(
            id=action_id,
            type=action_type,
            status=ActionStatus.PENDING,
            data=data,
            reason=reason,
            created_at=now,
            updated_at=now,
        )

        self._actions[action_id] = action
        self._save_to_redis(action)
        return action

    def get(self, action_id: str) -> ProposedAction | None:
        """Get an action by ID."""
        return self._actions.get(action_id)

    def list_pending(self) -> list[ProposedAction]:
        """List all pending actions."""
        return [a for a in self._actions.values() if a.status == ActionStatus.PENDING]

    def list_all(self, limit: int = 50) -> list[ProposedAction]:
        """List recent actions."""
        actions = sorted(
            self._actions.values(),
            key=lambda a: a.created_at,
            reverse=True,
        )
        return actions[:limit]

    def update_status(
        self,
        action_id: str,
        status: ActionStatus,
        error: str | None = None,
    ) -> ProposedAction | None:
        """Update action status."""
        action = self._actions.get(action_id)
        if action:
            action.status = status
            action.updated_at = datetime.now()
            if error:
                action.error = error
            self._save_to_redis(action)
        return action

    def delete(self, action_id: str) -> bool:
        """Delete an action."""
        if action_id in self._actions:
            del self._actions[action_id]
            self._delete_from_redis(action_id)
            return True
        return False

    def clear_old(self, hours: int = 24):
        """Clear actions older than specified hours."""
        cutoff = datetime.now()
        to_delete = [
            action_id
            for action_id, action in self._actions.items()
            if (cutoff - action.created_at).total_seconds() > hours * 3600
            and action.status != ActionStatus.PENDING
        ]
        for action_id in to_delete:
            del self._actions[action_id]
            self._delete_from_redis(action_id)


# Global action store
_action_store = ActionStore()


def get_action_store() -> ActionStore:
    """Get the global action store."""
    return _action_store


def format_action_for_chat(action: ProposedAction) -> str:
    """Format an action for display in chat."""
    lines = [f"**Proposed Action** (ID: {action.id})"]
    lines.append(f"Type: {action.type.value}")
    lines.append(f"Reason: {action.reason}")

    if action.type == ActionType.CREATE_TASK:
        data = action.data
        lines.append("\n**Task Details:**")
        lines.append(f"- Title: {data.get('title', 'Untitled')}")
        if data.get("body"):
            lines.append(f"- Description: {data['body']}")
        if data.get("due_date"):
            lines.append(f"- Due: {data['due_date']}")
        if data.get("importance") != "normal":
            lines.append(f"- Priority: {data['importance']}")

    elif action.type == ActionType.UPDATE_TASK:
        data = action.data
        lines.append("\n**Task Update:**")
        lines.append(f"- Task ID: {data.get('task_id')}")
        if data.get("title"):
            lines.append(f"- New Title: {data['title']}")
        if data.get("body"):
            lines.append(f"- New Description: {data['body']}")
        if data.get("due_date"):
            lines.append(f"- New Due Date: {data['due_date']}")
        if data.get("status"):
            lines.append(f"- Status: {data['status']}")
        if data.get("importance"):
            lines.append(f"- Priority: {data['importance']}")

    elif action.type == ActionType.CREATE_EVENT:
        data = action.data
        lines.append("\n**Event Details:**")
        lines.append(f"- Subject: {data.get('subject', 'Untitled')}")
        lines.append(f"- Start: {data.get('start_datetime', '')}")
        lines.append(f"- End: {data.get('end_datetime', '')}")
        if data.get("location"):
            lines.append(f"- Location: {data['location']}")
        if data.get("attendees"):
            lines.append(f"- Attendees: {', '.join(data['attendees'])}")

    elif action.type == ActionType.DRAFT_EMAIL:
        data = action.data
        lines.append("\n**Email Draft:**")
        lines.append(f"- To: {', '.join(data.get('to', []))}")
        lines.append(f"- Subject: {data.get('subject', '')}")
        lines.append(f"- Body:\n```\n{data.get('body', '')}\n```")

    lines.append(f"\n*Reply with 'approve {action.id}' or 'reject {action.id}'*")

    return "\n".join(lines)
