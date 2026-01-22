"""AI Actions service for managing proposed actions that require approval."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ActionType(str, Enum):
    """Types of actions the AI can propose."""

    CREATE_TASK = "create_task"
    CREATE_EVENT = "create_event"
    CREATE_NOTE = "create_note"
    EDIT_NOTE = "edit_note"
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


class ActionStore:
    """In-memory store for proposed actions."""

    def __init__(self):
        self._actions: dict[str, ProposedAction] = {}

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
        return action

    def delete(self, action_id: str) -> bool:
        """Delete an action."""
        if action_id in self._actions:
            del self._actions[action_id]
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
