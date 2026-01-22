"""AI Chat endpoints."""

import json
import re
from datetime import datetime, timedelta

from auth import get_access_token
from config import get_settings
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.actions import ActionType, get_action_store
from services.ai import generate_response, generate_response_stream
from services.graph import GraphClient
from services.vectors import get_collection_stats, ingest_document, search_documents

router = APIRouter(prefix="/chat", tags=["chat"])


def _parse_actions(response_text: str) -> tuple[str, list[dict]]:
    """Parse ACTION blocks from AI response and return cleaned response + actions."""
    action_pattern = r'```ACTION\s*\n?(.*?)\n?```'
    actions = []

    matches = re.findall(action_pattern, response_text, re.DOTALL)
    for match in matches:
        try:
            action_data = json.loads(match.strip())
            actions.append(action_data)
        except json.JSONDecodeError:
            pass  # Invalid JSON, skip

    # Remove ACTION blocks from response for cleaner display
    cleaned_response = re.sub(action_pattern, '', response_text, flags=re.DOTALL)
    cleaned_response = cleaned_response.strip()

    return cleaned_response, actions


def _create_action_from_data(action_data: dict) -> dict | None:
    """Create a proposed action from parsed data."""
    store = get_action_store()
    action_type_str = action_data.get("type", "")

    type_mapping = {
        "create_event": ActionType.CREATE_EVENT,
        "create_task": ActionType.CREATE_TASK,
        "create_note": ActionType.CREATE_NOTE,
        "edit_note": ActionType.EDIT_NOTE,
        "draft_email": ActionType.DRAFT_EMAIL,
    }

    action_type = type_mapping.get(action_type_str)
    if not action_type:
        return None

    # Prepare data based on action type
    data = {k: v for k, v in action_data.items() if k != "type"}

    # Create the action
    action = store.create(
        action_type=action_type,
        data=data,
        reason="Proposed by AI assistant",
    )

    return {
        "id": action.id,
        "type": action.type.value,
        "data": action.data,
    }


async def _get_tasks_context(token: str) -> str:
    """Fetch and format tasks for AI context."""
    client = GraphClient(token)
    tasks_text = []

    try:
        lists_result = await client.list_task_lists()
        lists = lists_result.get("value", [])

        for task_list in lists[:5]:  # Limit to 5 lists
            list_id = task_list.get("id")
            list_name = task_list.get("displayName", "Tasks")

            tasks_result = await client.list_tasks(list_id, include_completed=False)
            tasks = tasks_result.get("value", [])

            if tasks:
                tasks_text.append(f"\n## {list_name}")
                for task in tasks[:10]:  # Limit to 10 tasks per list
                    title = task.get("title", "Untitled")
                    status = task.get("status", "notStarted")
                    importance = task.get("importance", "normal")
                    due = task.get("dueDateTime", {}).get("dateTime", "")

                    task_line = f"- [{status}] {title}"
                    if importance == "high":
                        task_line += " (HIGH PRIORITY)"
                    if due:
                        task_line += f" (due: {due[:10]})"

                    tasks_text.append(task_line)

        return "\n".join(tasks_text) if tasks_text else ""
    except Exception as e:
        return f"[Error fetching tasks: {e}]"


async def _get_calendar_context(token: str) -> str:
    """Fetch and format calendar events for AI context."""
    client = GraphClient(token)

    try:
        # Get today's and tomorrow's events
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        end = (now + timedelta(days=2)).replace(hour=23, minute=59, second=59).isoformat() + "Z"

        result = await client.get_calendar_view(start, end)
        events = result.get("value", [])

        if not events:
            return "No upcoming events in the next 2 days."

        calendar_text = []
        current_date = None

        for event in events[:15]:  # Limit to 15 events
            subject = event.get("subject", "Untitled")
            start_info = event.get("start", {})
            location = event.get("location", {}).get("displayName", "")
            organizer = event.get("organizer", {}).get("emailAddress", {}).get("name", "")

            start_dt = start_info.get("dateTime", "")[:16]
            event_date = start_dt[:10]

            if event_date != current_date:
                current_date = event_date
                calendar_text.append(f"\n## {event_date}")

            event_line = f"- {start_dt[11:16]}: {subject}"
            if location:
                event_line += f" @ {location}"
            if organizer:
                event_line += f" (organizer: {organizer})"

            calendar_text.append(event_line)

        return "\n".join(calendar_text)
    except Exception as e:
        return f"[Error fetching calendar: {e}]"


async def _get_email_context(token: str) -> str:
    """Fetch and format recent emails for AI context."""
    client = GraphClient(token)

    try:
        result = await client.list_messages("inbox", top=10)
        messages = result.get("value", [])

        if not messages:
            return "No recent emails."

        email_text = []
        for msg in messages[:10]:
            from_info = msg.get("from", {}).get("emailAddress", {})
            subject = msg.get("subject", "(No subject)")
            sender = from_info.get("name", from_info.get("address", "Unknown"))
            received = msg.get("receivedDateTime", "")[:10]
            is_read = "read" if msg.get("isRead") else "unread"
            preview = msg.get("bodyPreview", "")[:100]

            email_text.append(f"- [{is_read}] {received} from {sender}: {subject}")
            if preview:
                email_text.append(f"  Preview: {preview}...")

        return "\n".join(email_text)
    except Exception as e:
        return f"[Error fetching emails: {e}]"


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str
    history: list[ChatMessage] | None = None
    use_context: bool = True  # Whether to use RAG
    include_tasks: bool = True  # Include tasks in context
    include_calendar: bool = True  # Include calendar in context
    include_email: bool = True  # Include recent emails in context


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    response: str
    context_used: bool
    sources: list[str] | None = None
    proposed_actions: list[dict] | None = None


@router.post("/send", response_model=ChatResponse)
async def send_message(request: Request, chat_request: ChatRequest):
    """Send a message and get a response."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    # Get notes context if enabled
    context = ""
    sources = []
    if chat_request.use_context:
        results = await search_documents(chat_request.message, k=5)
        if results:
            context_parts = []
            for result in results:
                source = result["source"]
                if source not in sources:
                    sources.append(source)
                context_parts.append(f"[From: {source}]\n{result['content']}")
            context = "\n\n---\n\n".join(context_parts)

    # Get tasks context
    tasks_context = ""
    if chat_request.include_tasks:
        tasks_context = await _get_tasks_context(token)

    # Get calendar context
    calendar_context = ""
    if chat_request.include_calendar:
        calendar_context = await _get_calendar_context(token)

    # Get email context
    email_context = ""
    if chat_request.include_email:
        email_context = await _get_email_context(token)

    # Convert history to expected format
    history = None
    if chat_request.history:
        history = [{"role": m.role, "content": m.content} for m in chat_request.history]

    # Generate response
    response = await generate_response(
        user_input=chat_request.message,
        context=context,
        tasks_context=tasks_context,
        calendar_context=calendar_context,
        email_context=email_context,
        chat_history=history,
        current_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    # Parse and create any proposed actions
    cleaned_response, parsed_actions = _parse_actions(response)
    proposed_actions = []
    for action_data in parsed_actions:
        created = _create_action_from_data(action_data)
        if created:
            proposed_actions.append(created)

    return ChatResponse(
        response=cleaned_response if cleaned_response else response,
        context_used=bool(context) or bool(tasks_context) or bool(calendar_context),
        sources=sources if sources else None,
        proposed_actions=proposed_actions if proposed_actions else None,
    )


@router.post("/stream")
async def stream_message(request: Request, chat_request: ChatRequest):
    """Send a message and stream the response."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    # Get notes context if enabled
    context = ""
    sources = []
    if chat_request.use_context:
        results = await search_documents(chat_request.message, k=5)
        if results:
            context_parts = []
            for result in results:
                source = result["source"]
                if source not in sources:
                    sources.append(source)
                context_parts.append(f"[From: {source}]\n{result['content']}")
            context = "\n\n---\n\n".join(context_parts)

    # Get tasks context
    tasks_context = ""
    if chat_request.include_tasks:
        tasks_context = await _get_tasks_context(token)

    # Get calendar context
    calendar_context = ""
    if chat_request.include_calendar:
        calendar_context = await _get_calendar_context(token)

    # Get email context
    email_context = ""
    if chat_request.include_email:
        email_context = await _get_email_context(token)

    # Convert history to expected format
    history = None
    if chat_request.history:
        history = [{"role": m.role, "content": m.content} for m in chat_request.history]

    async def generate():
        """Generate streaming response."""
        # First, send metadata
        yield f"data: {json.dumps({'type': 'meta', 'sources': sources})}\n\n"

        # Stream the response
        async for chunk in generate_response_stream(
            user_input=chat_request.message,
            context=context,
            tasks_context=tasks_context,
            calendar_context=calendar_context,
            email_context=email_context,
            chat_history=history,
            current_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/stats")
async def get_stats(request: Request):
    """Get vector store statistics."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stats = await get_collection_stats()
    return stats


@router.post("/ingest")
async def ingest_all_notes(request: Request):
    """Re-ingest all notes into the vector store."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    settings = get_settings()
    client = GraphClient(token)
    ingested = 0
    errors = []

    # Get all folders
    try:
        folders_result = await client.list_folder(settings.onedrive_base_folder)
        folders = [item["name"] for item in folders_result.get("value", []) if "folder" in item]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list folders: {e}") from e

    # Ingest notes from each folder
    for folder in folders:
        if folder.startswith("_"):  # Skip system folders like _index
            continue

        try:
            folder_path = f"{settings.onedrive_base_folder}/{folder}"
            notes_result = await client.list_folder(folder_path)

            for item in notes_result.get("value", []):
                if "file" not in item or not item["name"].endswith(".md"):
                    continue

                try:
                    note_path = f"{folder_path}/{item['name']}"
                    content = await client.get_file_content(note_path)

                    await ingest_document(
                        content=content.decode("utf-8"),
                        source_path=note_path,
                        metadata={"folder": folder, "filename": item["name"]},
                    )
                    ingested += 1
                except Exception as e:
                    errors.append(f"{folder}/{item['name']}: {e!s}")
        except Exception as e:
            errors.append(f"Folder {folder}: {e!s}")

    return {
        "ingested": ingested,
        "errors": errors if errors else None,
    }


HISTORY_FILE_PATH = "_system/chat_history.json"


@router.get("/history")
async def get_conversation_history(request: Request):
    """Get conversation history from OneDrive."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    settings = get_settings()
    client = GraphClient(token)
    file_path = f"{settings.onedrive_base_folder}/{HISTORY_FILE_PATH}"

    try:
        content = await client.get_file_content(file_path)
        history = json.loads(content.decode("utf-8"))
        return {"conversations": history.get("conversations", [])}
    except Exception:
        # File doesn't exist yet, return empty history
        return {"conversations": []}


@router.post("/history")
async def save_conversation_history(request: Request):
    """Save conversation history to OneDrive."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    body = await request.json()
    conversations = body.get("conversations", [])

    settings = get_settings()
    client = GraphClient(token)

    # Ensure _system folder exists
    try:
        await client.list_folder(f"{settings.onedrive_base_folder}/_system")
    except Exception:
        try:
            await client.create_folder(settings.onedrive_base_folder, "_system")
        except Exception:
            pass  # Folder might already exist

    file_path = f"{settings.onedrive_base_folder}/{HISTORY_FILE_PATH}"
    content = json.dumps({"conversations": conversations}, indent=2)

    try:
        await client.upload_file(file_path, content.encode("utf-8"))
        return {"status": "saved", "count": len(conversations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save history: {e}") from e


@router.delete("/history/{conversation_id}")
async def delete_conversation(request: Request, conversation_id: str):
    """Delete a specific conversation from history."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    settings = get_settings()
    client = GraphClient(token)
    file_path = f"{settings.onedrive_base_folder}/{HISTORY_FILE_PATH}"

    try:
        # Load existing history
        content = await client.get_file_content(file_path)
        history = json.loads(content.decode("utf-8"))
        conversations = history.get("conversations", [])

        # Filter out the conversation to delete
        updated = [c for c in conversations if c.get("id") != conversation_id]

        # Save back
        new_content = json.dumps({"conversations": updated}, indent=2)
        await client.upload_file(file_path, new_content.encode("utf-8"))

        return {"status": "deleted", "id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {e}") from e
