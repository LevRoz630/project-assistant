"""AI Chat endpoints."""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta

from ..auth import get_access_token
from ..config import get_settings
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from ..services.actions import ActionType, get_action_store
from ..services.ai import generate_response, generate_response_stream
from ..services.graph import GraphClient
from ..services.prompts import detect_role
from ..services.sanitization import PromptSanitizer
from ..services.sanitization import (
    sanitize_calendar_content,
    sanitize_email_content,
    sanitize_note_content,
    sanitize_task_content,
)
from ..services.search import execute_searches
from ..services.security import SecurityEventType, log_security_event
from ..services.vectors import get_collection_stats, ingest_document, search_documents
from ..services.web_fetch import fetch_urls
from ..services.context_cache import get_cached_context, set_cached_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


def _parse_actions(response_text: str) -> tuple[str, list[dict]]:
    """Parse ACTION blocks from AI response and return cleaned response + actions."""
    action_pattern = r'```ACTION\s*\n?(.*?)\n?```'
    actions = []

    matches = re.findall(action_pattern, response_text, re.DOTALL)
    for match in matches:
        try:
            action_data = json.loads(match.strip())
            actions.append(action_data)
        except json.JSONDecodeError as e:
            logger.debug(f"Skipping invalid ACTION JSON: {e}")

    # Remove ACTION blocks from response for cleaner display
    cleaned_response = re.sub(action_pattern, '', response_text, flags=re.DOTALL)
    cleaned_response = cleaned_response.strip()

    return cleaned_response, actions


def _parse_searches(response_text: str) -> tuple[str, list[str]]:
    """Parse SEARCH blocks from AI response and return cleaned response + queries."""
    search_pattern = r'```SEARCH\s*\n?(.*?)\n?```'
    queries = []

    matches = re.findall(search_pattern, response_text, re.DOTALL)
    for match in matches:
        try:
            search_data = json.loads(match.strip())
            query = search_data.get("query", "")
            if query:
                # Sanitize the search query with injection filtering enabled
                sanitized_query = PromptSanitizer.sanitize(query, max_length=200, filter_injections=True)
                # Only add if not filtered
                if sanitized_query != "[Content filtered for security]":
                    queries.append(sanitized_query)
        except json.JSONDecodeError:
            # Maybe it's just a plain query string
            query = match.strip()
            if query:
                sanitized_query = PromptSanitizer.sanitize(query, max_length=200, filter_injections=True)
                # Only add if not filtered
                if sanitized_query != "[Content filtered for security]":
                    queries.append(sanitized_query)

    # Remove SEARCH blocks from response for cleaner display
    cleaned_response = re.sub(search_pattern, '', response_text, flags=re.DOTALL)
    cleaned_response = cleaned_response.strip()

    return cleaned_response, queries


def _parse_fetches(response_text: str) -> tuple[str, list[str]]:
    """Parse FETCH blocks from AI response and return cleaned response + URLs."""
    fetch_pattern = r'```FETCH\s*\n?(.*?)\n?```'
    urls = []

    matches = re.findall(fetch_pattern, response_text, re.DOTALL)
    for match in matches:
        try:
            fetch_data = json.loads(match.strip())
            url = fetch_data.get("url", "")
            if url:
                # Basic URL validation
                if url.startswith(("http://", "https://")):
                    urls.append(url)
        except json.JSONDecodeError:
            # Maybe it's just a plain URL string
            url = match.strip()
            if url.startswith(("http://", "https://")):
                urls.append(url)

    # Remove FETCH blocks from response for cleaner display
    cleaned_response = re.sub(fetch_pattern, '', response_text, flags=re.DOTALL)
    cleaned_response = cleaned_response.strip()

    return cleaned_response, urls


def _create_action_from_data(action_data: dict) -> dict | None:
    """Create a proposed action from parsed data."""
    store = get_action_store()
    action_type_str = action_data.get("type", "")

    type_mapping = {
        "create_event": ActionType.CREATE_EVENT,
        "create_task": ActionType.CREATE_TASK,
        "create_note": ActionType.CREATE_NOTE,
        "edit_note": ActionType.EDIT_NOTE,
        "move_note": ActionType.MOVE_NOTE,
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
        lists = lists_result.get("value", [])[:5]  # Limit to 5 lists

        # Fetch all task lists IN PARALLEL for better performance
        async def fetch_list_tasks(task_list):
            list_id = task_list.get("id")
            list_name = task_list.get("displayName", "Tasks")
            tasks_result = await client.list_tasks(list_id, include_completed=False)
            return list_name, tasks_result.get("value", [])

        results = await asyncio.gather(*[fetch_list_tasks(tl) for tl in lists])

        # Format results
        for list_name, tasks in results:
            if tasks:
                tasks_text.append(f"\n## {list_name}")
                for task in tasks[:10]:  # Limit to 10 tasks per list
                    title, _ = sanitize_task_content(
                        task.get("title", "Untitled"),
                        task.get("body", {}).get("content"),
                    )
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
            subject, location, organizer = sanitize_calendar_content(
                event.get("subject", "Untitled"),
                event.get("location", {}).get("displayName"),
                event.get("organizer", {}).get("emailAddress", {}).get("name"),
            )
            start_info = event.get("start", {})

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
            raw_sender = from_info.get("name", from_info.get("address", "Unknown"))
            raw_subject = msg.get("subject", "(No subject)")
            raw_preview = msg.get("bodyPreview", "")

            sender, subject, preview = sanitize_email_content(
                raw_sender, raw_subject, raw_preview
            )
            received = msg.get("receivedDateTime", "")[:10]
            is_read = "read" if msg.get("isRead") else "unread"

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


MAX_CHAT_HISTORY_LENGTH = 100  # Maximum number of messages in history


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str
    history: list[ChatMessage] | None = None
    use_context: bool = True  # Whether to use RAG
    include_tasks: bool = True  # Include tasks in context
    include_calendar: bool = True  # Include calendar in context
    include_email: bool = True  # Include recent emails in context

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate and clean message input."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 10000:
            raise ValueError("Message too long (max 10000 characters)")
        return v.strip()

    @field_validator("history")
    @classmethod
    def validate_history(cls, v: list[ChatMessage] | None) -> list[ChatMessage] | None:
        """Validate chat history length to prevent memory issues."""
        if v is None:
            return v
        if len(v) > MAX_CHAT_HISTORY_LENGTH:
            raise ValueError(f"Chat history too long (max {MAX_CHAT_HISTORY_LENGTH} messages)")
        return v


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

    # Check user input for potential injection attempts
    if PromptSanitizer.contains_injection_attempt(chat_request.message):
        log_security_event(
            SecurityEventType.INJECTION_ATTEMPT,
            session_id,
            {"source": "user_message", "message_length": len(chat_request.message)},
        )
        # We log but still allow the message - the AI is instructed to ignore manipulations
        # For stricter security, you could return an error here instead

    # Fetch all context in parallel for better performance
    async def get_notes_context():
        if not chat_request.use_context:
            return "", []
        try:
            results = await asyncio.wait_for(
                search_documents(chat_request.message, k=5),
                timeout=15.0
            )
            if results:
                context_parts = []
                sources = []
                for result in results:
                    content, source = sanitize_note_content(
                        result["content"], result["source"]
                    )
                    if source not in sources:
                        sources.append(source)
                    context_parts.append(f"[From: {source}]\n{content}")
                return "\n\n---\n\n".join(context_parts), sources
        except asyncio.TimeoutError:
            logger.warning("Notes context fetch timed out")
        except Exception as e:
            logger.warning(f"Notes context fetch failed: {e}")
        return "", []

    async def get_tasks():
        if not chat_request.include_tasks:
            return ""
        # Check cache first
        cached = get_cached_context("tasks", session_id)
        if cached:
            return cached
        try:
            result = await asyncio.wait_for(_get_tasks_context(token), timeout=20.0)
            # Cache if successful (don't cache error messages)
            if result and not result.startswith("["):
                set_cached_context("tasks", session_id, result)
            return result
        except asyncio.TimeoutError:
            logger.warning("Tasks context fetch timed out")
            return "[Tasks unavailable - request timed out]"
        except Exception as e:
            logger.warning(f"Tasks context fetch failed: {e}")
            return f"[Tasks unavailable: {e}]"

    async def get_calendar():
        if not chat_request.include_calendar:
            return ""
        # Check cache first
        cached = get_cached_context("calendar", session_id)
        if cached:
            return cached
        try:
            result = await asyncio.wait_for(_get_calendar_context(token), timeout=20.0)
            # Cache if successful (don't cache error messages)
            if result and not result.startswith("["):
                set_cached_context("calendar", session_id, result)
            return result
        except asyncio.TimeoutError:
            logger.warning("Calendar context fetch timed out")
            return "[Calendar unavailable - request timed out]"
        except Exception as e:
            logger.warning(f"Calendar context fetch failed: {e}")
            return f"[Calendar unavailable: {e}]"

    async def get_email():
        if not chat_request.include_email:
            return ""
        # Check cache first
        cached = get_cached_context("email", session_id)
        if cached:
            return cached
        try:
            result = await asyncio.wait_for(_get_email_context(token), timeout=20.0)
            # Cache if successful (don't cache error messages)
            if result and not result.startswith("["):
                set_cached_context("email", session_id, result)
            return result
        except asyncio.TimeoutError:
            logger.warning("Email context fetch timed out")
            return "[Email unavailable - request timed out]"
        except Exception as e:
            logger.warning(f"Email context fetch failed: {e}")
            return f"[Email unavailable: {e}]"

    # Run all context fetches in parallel
    notes_result, tasks_context, calendar_context, email_context = await asyncio.gather(
        get_notes_context(),
        get_tasks(),
        get_calendar(),
        get_email(),
    )
    context, sources = notes_result

    # Convert history to expected format
    history = None
    if chat_request.history:
        history = [{"role": m.role, "content": m.content} for m in chat_request.history]

    # Detect role from message
    role = detect_role(chat_request.message)

    # Generate initial response with timeout
    try:
        response = await asyncio.wait_for(
            generate_response(
                user_input=chat_request.message,
                context=context,
                tasks_context=tasks_context,
                calendar_context=calendar_context,
                email_context=email_context,
                chat_history=history,
                current_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                role=role,
            ),
            timeout=90.0  # 90 second timeout for LLM response
        )
    except asyncio.TimeoutError:
        logger.error("LLM response generation timed out")
        raise HTTPException(status_code=504, detail="AI response took too long. Please try a simpler question.")
    except Exception as e:
        logger.error(f"LLM response generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")

    # Check for search requests if web search is enabled
    search_results_context = ""
    if settings.enable_web_search:
        cleaned_after_search, search_queries = _parse_searches(response)

        if search_queries:
            # Execute searches with timeout
            try:
                search_results_context = await asyncio.wait_for(
                    execute_searches(search_queries),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Web search timed out")
                search_results_context = ""

            if search_results_context:
                # Re-generate response with search results
                augmented_context = context
                if search_results_context:
                    augmented_context = f"{context}\n\n===== WEB SEARCH RESULTS =====\n{search_results_context}\n===== END WEB SEARCH RESULTS =====" if context else f"===== WEB SEARCH RESULTS =====\n{search_results_context}\n===== END WEB SEARCH RESULTS ====="

                try:
                    response = await asyncio.wait_for(
                        generate_response(
                            user_input=chat_request.message,
                            context=augmented_context,
                            tasks_context=tasks_context,
                            calendar_context=calendar_context,
                            email_context=email_context,
                            chat_history=history,
                            current_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            role=role,
                        ),
                        timeout=90.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("LLM re-generation with search results timed out, using initial response")

    # Check for URL fetch requests if enabled
    fetch_results_context = ""
    if settings.enable_url_fetch:
        cleaned_after_fetch, fetch_urls_list = _parse_fetches(response)

        if fetch_urls_list:
            # Fetch URL contents with timeout
            try:
                fetch_results_context = await asyncio.wait_for(
                    fetch_urls(fetch_urls_list),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("URL fetch timed out")
                fetch_results_context = ""

            if fetch_results_context:
                # Re-generate response with fetched content
                augmented_context = context
                if search_results_context:
                    augmented_context = f"{augmented_context}\n\n===== WEB SEARCH RESULTS =====\n{search_results_context}\n===== END WEB SEARCH RESULTS =====" if augmented_context else f"===== WEB SEARCH RESULTS =====\n{search_results_context}\n===== END WEB SEARCH RESULTS ====="
                if fetch_results_context:
                    augmented_context = f"{augmented_context}\n\n===== FETCHED PAGE CONTENT =====\n{fetch_results_context}\n===== END FETCHED PAGE CONTENT =====" if augmented_context else f"===== FETCHED PAGE CONTENT =====\n{fetch_results_context}\n===== END FETCHED PAGE CONTENT ====="

                try:
                    response = await asyncio.wait_for(
                        generate_response(
                            user_input=chat_request.message,
                            context=augmented_context,
                            tasks_context=tasks_context,
                            calendar_context=calendar_context,
                            email_context=email_context,
                            chat_history=history,
                            current_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            role=role,
                        ),
                        timeout=90.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("LLM re-generation with fetch results timed out, using previous response")

    # Parse and create any proposed actions
    cleaned_response, parsed_actions = _parse_actions(response)
    proposed_actions = []
    for action_data in parsed_actions:
        created = _create_action_from_data(action_data)
        if created:
            proposed_actions.append(created)

    return ChatResponse(
        response=cleaned_response if cleaned_response else response,
        context_used=bool(context) or bool(tasks_context) or bool(calendar_context) or bool(search_results_context) or bool(fetch_results_context),
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

    # Check user input for potential injection attempts
    if PromptSanitizer.contains_injection_attempt(chat_request.message):
        log_security_event(
            SecurityEventType.INJECTION_ATTEMPT,
            session_id,
            {"source": "user_message_stream", "message_length": len(chat_request.message)},
        )

    # Fetch all context in parallel for better performance
    async def get_notes_context():
        if not chat_request.use_context:
            return "", []
        try:
            results = await asyncio.wait_for(
                search_documents(chat_request.message, k=5),
                timeout=15.0
            )
            if results:
                context_parts = []
                sources = []
                for result in results:
                    content, source = sanitize_note_content(
                        result["content"], result["source"]
                    )
                    if source not in sources:
                        sources.append(source)
                    context_parts.append(f"[From: {source}]\n{content}")
                return "\n\n---\n\n".join(context_parts), sources
        except asyncio.TimeoutError:
            logger.warning("Notes context fetch timed out (stream)")
        except Exception as e:
            logger.warning(f"Notes context fetch failed (stream): {e}")
        return "", []

    async def get_tasks():
        if not chat_request.include_tasks:
            return ""
        # Check cache first
        cached = get_cached_context("tasks", session_id)
        if cached:
            return cached
        try:
            result = await asyncio.wait_for(_get_tasks_context(token), timeout=20.0)
            # Cache if successful
            if result and not result.startswith("["):
                set_cached_context("tasks", session_id, result)
            return result
        except asyncio.TimeoutError:
            logger.warning("Tasks context fetch timed out (stream)")
            return ""
        except Exception as e:
            logger.warning(f"Tasks context fetch failed (stream): {e}")
            return ""

    async def get_calendar():
        if not chat_request.include_calendar:
            return ""
        # Check cache first
        cached = get_cached_context("calendar", session_id)
        if cached:
            return cached
        try:
            result = await asyncio.wait_for(_get_calendar_context(token), timeout=20.0)
            # Cache if successful
            if result and not result.startswith("["):
                set_cached_context("calendar", session_id, result)
            return result
        except asyncio.TimeoutError:
            logger.warning("Calendar context fetch timed out (stream)")
            return ""
        except Exception as e:
            logger.warning(f"Calendar context fetch failed (stream): {e}")
            return ""

    async def get_email():
        if not chat_request.include_email:
            return ""
        # Check cache first
        cached = get_cached_context("email", session_id)
        if cached:
            return cached
        try:
            result = await asyncio.wait_for(_get_email_context(token), timeout=20.0)
            # Cache if successful
            if result and not result.startswith("["):
                set_cached_context("email", session_id, result)
            return result
        except asyncio.TimeoutError:
            logger.warning("Email context fetch timed out (stream)")
            return ""
        except Exception as e:
            logger.warning(f"Email context fetch failed (stream): {e}")
            return ""

    # Run all context fetches in parallel
    notes_result, tasks_context, calendar_context, email_context = await asyncio.gather(
        get_notes_context(),
        get_tasks(),
        get_calendar(),
        get_email(),
    )
    context, sources = notes_result

    # Convert history to expected format
    history = None
    if chat_request.history:
        history = [{"role": m.role, "content": m.content} for m in chat_request.history]

    # Detect role from message
    role = detect_role(chat_request.message)

    async def generate():
        """Generate streaming response."""
        try:
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
                role=role,
            ):
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.exception("Error during response streaming")
            # Always send done message so client doesn't hang
            yield f"data: {json.dumps({'type': 'error', 'error': 'Stream interrupted'})}\n\n"
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


from ..services.chat_history import (
    get_chat_history,
    save_chat_history,
    delete_conversation as delete_chat_conversation,
)


@router.get("/history")
async def get_conversation_history(request: Request):
    """Get conversation history from Redis."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    conversations = get_chat_history(session_id)
    return {"conversations": conversations}


@router.post("/history")
async def save_conversation_history(request: Request):
    """Save conversation history to Redis (keeps last 10)."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    conversations = body.get("conversations", [])

    success = save_chat_history(session_id, conversations)

    if not success:
        # Redis not available - return success anyway but log warning
        logger.warning("Chat history not saved - Redis unavailable")

    return {"status": "saved", "count": min(len(conversations), 10)}


@router.delete("/history/{conversation_id}")
async def delete_conversation_endpoint(request: Request, conversation_id: str):
    """Delete a specific conversation from history."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = delete_chat_conversation(session_id, conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "deleted", "id": conversation_id}
