"""Joplin notes integration endpoints."""

from datetime import datetime

from config import get_settings
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from services.joplin import JoplinClient
from services.vectors import delete_document, ingest_document

router = APIRouter(prefix="/joplin", tags=["joplin"])
settings = get_settings()


def get_joplin_client(request: Request) -> JoplinClient:
    """Dependency to get Joplin client if enabled."""
    if not settings.joplin_enabled:
        raise HTTPException(status_code=503, detail="Joplin integration is not enabled")

    if not settings.joplin_token:
        raise HTTPException(status_code=503, detail="Joplin token not configured")

    # Still require authentication for the app
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return JoplinClient()


class NoteCreate(BaseModel):
    """Request body for creating a note."""

    notebook: str  # Notebook name (will find or create)
    title: str
    body: str
    is_todo: bool = False


class NoteUpdate(BaseModel):
    """Request body for updating a note."""

    title: str | None = None
    body: str | None = None


# ==================== Health ====================


@router.get("/status")
async def get_status():
    """Check Joplin connection status."""
    if not settings.joplin_enabled:
        return {"enabled": False, "connected": False, "message": "Joplin integration disabled"}

    if not settings.joplin_token:
        return {"enabled": True, "connected": False, "message": "Joplin token not configured"}

    client = JoplinClient()
    connected = await client.ping()

    return {
        "enabled": True,
        "connected": connected,
        "message": "Connected to Joplin" if connected else "Cannot reach Joplin - is it running?",
    }


# ==================== Notebooks ====================


@router.get("/notebooks")
async def list_notebooks(client: JoplinClient = Depends(get_joplin_client)):
    """List all Joplin notebooks."""
    try:
        notebooks = await client.list_notebooks()

        # Build hierarchy info
        notebook_map = {nb["id"]: nb for nb in notebooks}
        result = []
        for nb in notebooks:
            parent_title = None
            if nb.get("parent_id") and nb["parent_id"] in notebook_map:
                parent_title = notebook_map[nb["parent_id"]].get("title")

            result.append({
                "id": nb["id"],
                "title": nb["title"],
                "parent_id": nb.get("parent_id"),
                "parent_title": parent_title,
                "created": _format_timestamp(nb.get("created_time")),
                "modified": _format_timestamp(nb.get("updated_time")),
            })

        return {"notebooks": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notebooks")
async def create_notebook(
    title: str,
    parent_id: str | None = None,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Create a new notebook."""
    try:
        result = await client.create_notebook(title, parent_id)
        return {"success": True, "notebook": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/notebooks/{notebook_id}")
async def delete_notebook(
    notebook_id: str,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Delete a notebook."""
    try:
        await client.delete_notebook(notebook_id)
        return {"success": True, "deleted": notebook_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Notes ====================


@router.get("/notes")
async def list_notes(
    notebook: str | None = None,
    limit: int = 100,
    client: JoplinClient = Depends(get_joplin_client),
):
    """List notes, optionally filtered by notebook name."""
    try:
        notebook_id = None
        if notebook:
            nb = await client.get_notebook_by_title(notebook)
            if not nb:
                return {"notebook": notebook, "notes": [], "error": "Notebook not found"}
            notebook_id = nb["id"]

        notes = await client.list_notes(notebook_id=notebook_id, limit=limit)

        result = []
        for note in notes:
            result.append({
                "id": note["id"],
                "title": note["title"],
                "notebook_id": note.get("parent_id"),
                "created": _format_timestamp(note.get("created_time")),
                "modified": _format_timestamp(note.get("updated_time")),
                "is_todo": note.get("is_todo") == 1,
                "completed": note.get("todo_completed") == 1 if note.get("is_todo") else None,
            })

        return {"notebook": notebook, "notes": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/notes/{note_id}")
async def get_note(
    note_id: str,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Get a specific note by ID."""
    try:
        note = await client.get_note(note_id)

        return {
            "id": note["id"],
            "title": note["title"],
            "body": note.get("body", ""),
            "notebook_id": note.get("parent_id"),
            "created": _format_timestamp(note.get("created_time")),
            "modified": _format_timestamp(note.get("updated_time")),
            "is_todo": note.get("is_todo") == 1,
        }
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notes")
async def create_note(
    note: NoteCreate,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Create a new note."""
    try:
        # Find or create notebook
        notebook = await client.get_notebook_by_title(note.notebook)
        if not notebook:
            notebook = await client.create_notebook(note.notebook)

        result = await client.create_note(
            title=note.title,
            body=note.body,
            notebook_id=notebook["id"],
            is_todo=note.is_todo,
        )

        # Index in vector store
        source_path = f"joplin://{notebook['id']}/{result['id']}"
        await ingest_document(
            content=f"# {note.title}\n\n{note.body}",
            source_path=source_path,
            metadata={
                "source": "joplin",
                "notebook": note.notebook,
                "title": note.title,
                "note_id": result["id"],
            },
        )

        return {
            "success": True,
            "id": result["id"],
            "title": result.get("title"),
            "notebook": note.notebook,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/notes/{note_id}")
async def update_note(
    note_id: str,
    note: NoteUpdate,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Update a note."""
    try:
        result = await client.update_note(
            note_id=note_id,
            title=note.title,
            body=note.body,
        )

        # Re-index if body was updated
        if note.body is not None:
            existing = await client.get_note(note_id)
            source_path = f"joplin://{existing.get('parent_id')}/{note_id}"
            await ingest_document(
                content=f"# {existing.get('title', '')}\n\n{note.body}",
                source_path=source_path,
                metadata={
                    "source": "joplin",
                    "title": existing.get("title"),
                    "note_id": note_id,
                },
            )

        return {"success": True, "id": note_id}
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Delete a note."""
    try:
        # Get note info for vector store cleanup
        note = await client.get_note(note_id, include_body=False)
        source_path = f"joplin://{note.get('parent_id')}/{note_id}"

        await client.delete_note(note_id)
        await delete_document(source_path)

        return {"success": True, "deleted": note_id}
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Search ====================


@router.get("/search")
async def search_notes(
    q: str,
    limit: int = 20,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Search notes in Joplin."""
    try:
        notes = await client.search(q, limit=limit)

        result = []
        for note in notes:
            result.append({
                "id": note["id"],
                "title": note["title"],
                "notebook_id": note.get("parent_id"),
                "created": _format_timestamp(note.get("created_time")),
                "modified": _format_timestamp(note.get("updated_time")),
            })

        return {"query": q, "results": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Tags ====================


@router.get("/tags")
async def list_tags(client: JoplinClient = Depends(get_joplin_client)):
    """List all tags."""
    try:
        tags = await client.list_tags()
        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notes/{note_id}/tags")
async def add_tag(
    note_id: str,
    tag_name: str,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Add a tag to a note (creates tag if it doesn't exist)."""
    try:
        tag = await client.get_or_create_tag(tag_name)
        await client.add_tag_to_note(tag["id"], note_id)
        return {"success": True, "tag": tag_name, "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/notes/{note_id}/tags/{tag_name}")
async def remove_tag(
    note_id: str,
    tag_name: str,
    client: JoplinClient = Depends(get_joplin_client),
):
    """Remove a tag from a note."""
    try:
        tags = await client.list_tags()
        tag = next((t for t in tags if t["title"] == tag_name), None)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        await client.remove_tag_from_note(tag["id"], note_id)
        return {"success": True, "removed": tag_name, "note_id": note_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Diary Integration ====================


@router.post("/diary/today")
async def create_today_diary(client: JoplinClient = Depends(get_joplin_client)):
    """Create or get today's diary entry in Joplin."""
    today = datetime.now().strftime("%Y-%m-%d")
    title = today

    try:
        # Check if Diary notebook exists
        diary_notebook = await client.get_notebook_by_title("Diary")
        if not diary_notebook:
            diary_notebook = await client.create_notebook("Diary")

        # Search for today's entry
        notes = await client.list_notes(notebook_id=diary_notebook["id"])
        existing = next((n for n in notes if n["title"] == title), None)

        if existing:
            note = await client.get_note(existing["id"])
            return {
                "exists": True,
                "id": note["id"],
                "title": note["title"],
                "body": note.get("body", ""),
            }

        # Create new diary entry
        template = f"""# {today}

## Morning

## Tasks for Today
- [ ]

## Notes

## Evening Reflection

"""
        result = await client.create_note(
            title=title,
            body=template,
            notebook_id=diary_notebook["id"],
        )

        # Index
        source_path = f"joplin://{diary_notebook['id']}/{result['id']}"
        await ingest_document(
            content=template,
            source_path=source_path,
            metadata={
                "source": "joplin",
                "notebook": "Diary",
                "title": title,
                "type": "diary",
            },
        )

        return {
            "exists": False,
            "created": True,
            "id": result["id"],
            "title": title,
            "body": template,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _format_timestamp(ts: int | None) -> str | None:
    """Convert Joplin timestamp (ms) to ISO format."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts / 1000).isoformat()
