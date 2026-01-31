"""Notes CRUD endpoints - OneDrive integration."""

import contextlib
import logging
from datetime import datetime

from ..auth import get_access_token_for_service
from ..config import get_settings
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from ..services.graph import GraphClient
from ..services.security import safe_error_message
from ..services.vectors import delete_document, ingest_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["notes"])
settings = get_settings()


def _validate_path_component(value: str, field_name: str) -> str:
    """Validate a path component (folder or filename) to prevent path traversal attacks."""
    if not value:
        raise HTTPException(status_code=400, detail=f"{field_name} cannot be empty")

    # Reject path traversal attempts
    if ".." in value:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: path traversal not allowed")

    # Reject absolute paths
    if value.startswith("/") or value.startswith("\\"):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: absolute paths not allowed")

    # Reject paths containing slashes (except for filename:path which FastAPI handles)
    if "/" in value or "\\" in value:
        # Allow forward slashes in filenames since FastAPI's :path converter handles nested paths
        # But still reject backslashes and double slashes
        if "\\" in value or "//" in value:
            raise HTTPException(status_code=400, detail=f"Invalid {field_name}: invalid path characters")

    # Reject null bytes
    if "\x00" in value:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: null bytes not allowed")

    return value


def get_graph_client(request: Request) -> GraphClient:
    """Dependency to get authenticated Graph client for notes/storage."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token_for_service(session_id, "notes")
    if not token:
        raise HTTPException(
            status_code=401, detail="Session expired or no storage account configured"
        )

    return GraphClient(token)


class NoteCreate(BaseModel):
    """Request body for creating a note."""

    folder: str  # e.g., "Diary", "Projects", "Study", "Inbox"
    filename: str  # e.g., "2026-01-21.md" or "my-note.md"
    content: str


class NoteUpdate(BaseModel):
    """Request body for updating a note."""

    content: str


def get_note_path(folder: str, filename: str) -> str:
    """Construct the full OneDrive path for a note."""
    return f"{settings.onedrive_base_folder}/{folder}/{filename}"


@router.get("/folders")
async def list_folders(client: GraphClient = Depends(get_graph_client)):
    """List all note folders."""
    try:
        result = await client.list_folder(settings.onedrive_base_folder)
        # Exclude system/hidden folders (.obsidian, _system, etc.)
        excluded = {".obsidian", ".trash", "_system"}
        folders = [
            {
                "name": item["name"],
                "id": item["id"],
                "created": item.get("createdDateTime"),
                "modified": item.get("lastModifiedDateTime"),
            }
            for item in result.get("value", [])
            if "folder" in item and item["name"] not in excluded and not item["name"].startswith(".")
        ]
        return {"folders": folders}
    except Exception as e:
        # If folder doesn't exist, create it
        if "itemNotFound" in str(e):
            await _ensure_folder_structure(client)
            return {"folders": ["Diary", "Projects", "Study", "Inbox"]}
        raise HTTPException(
            status_code=500, detail=safe_error_message(e, "List folders")
        ) from e


@router.get("/list/{folder}")
async def list_notes(folder: str, client: GraphClient = Depends(get_graph_client)):
    """List all notes in a folder."""
    _validate_path_component(folder, "folder")
    try:
        folder_path = f"{settings.onedrive_base_folder}/{folder}"
        result = await client.list_folder(folder_path)

        notes = [
            {
                "name": item["name"],
                "id": item["id"],
                "path": f"{folder}/{item['name']}",
                "size": item.get("size", 0),
                "created": item.get("createdDateTime"),
                "modified": item.get("lastModifiedDateTime"),
            }
            for item in result.get("value", [])
            if "file" in item and item["name"].endswith(".md")
        ]

        # Sort by modified date, newest first
        notes.sort(key=lambda x: x.get("modified", ""), reverse=True)

        return {"folder": folder, "notes": notes}
    except Exception as e:
        if "itemNotFound" in str(e):
            return {"folder": folder, "notes": []}
        raise HTTPException(
            status_code=500, detail=safe_error_message(e, "List notes")
        ) from e


@router.get("/content/{folder}/{filename:path}")
async def get_note(
    folder: str,
    filename: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Get the content of a note. Auto-creates if it doesn't exist."""
    _validate_path_component(folder, "folder")
    _validate_path_component(filename, "filename")
    note_path = get_note_path(folder, filename)

    try:
        content = await client.get_file_content(note_path)
        metadata = await client.get_item_by_path(note_path)

        return {
            "folder": folder,
            "filename": filename,
            "content": content.decode("utf-8"),
            "modified": metadata.get("lastModifiedDateTime"),
            "created": metadata.get("createdDateTime"),
        }
    except Exception as e:
        error_str = str(e).lower()
        if "itemnotfound" in error_str or "404" in error_str or "not found" in error_str:
            try:
                return await _auto_create_note(client, folder, filename)
            except Exception as create_err:
                logger.error(f"Failed to auto-create note {note_path}: {create_err}")
                raise HTTPException(
                    status_code=500, detail=safe_error_message(create_err, "Create note")
                ) from create_err
        logger.error(f"Failed to load note {note_path}: {e}")
        raise HTTPException(
            status_code=500, detail=safe_error_message(e, "Load note")
        ) from e


def _escape_yaml_string(value: str) -> str:
    """Escape a string for safe inclusion in YAML frontmatter."""
    # If the value contains special YAML characters, quote it
    if any(c in value for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`', '\n']):
        # Escape any existing double quotes and wrap in double quotes
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return value


async def _auto_create_note(client: GraphClient, folder: str, filename: str) -> dict:
    """Auto-create a note with date metadata."""
    today = datetime.now()
    note_title = filename.replace(".md", "") if filename.endswith(".md") else filename
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    # Escape user input for YAML safety
    safe_title = _escape_yaml_string(note_title)
    safe_folder = _escape_yaml_string(folder)

    template = f"""---
title: {safe_title}
created: {today.strftime("%Y-%m-%d %H:%M")}
folder: {safe_folder}
---

# {note_title}

"""

    note_path = get_note_path(folder, filename)

    await _ensure_folder_structure(client, folder)
    await client.upload_file(note_path, template.encode("utf-8"))

    # Index in vector store
    indexed = False
    try:
        await ingest_document(
            content=template,
            source_path=note_path,
            metadata={"folder": folder, "filename": filename},
        )
        indexed = True
    except Exception as e:
        logger.warning(f"Failed to index note {note_path}: {e}")

    return {
        "folder": folder,
        "filename": filename,
        "content": template,
        "created": today.isoformat(),
        "modified": today.isoformat(),
        "auto_created": True,
        "indexed": indexed,
    }


@router.post("/create")
async def create_note(
    note: NoteCreate,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a new note."""
    _validate_path_component(note.folder, "folder")
    _validate_path_component(note.filename, "filename")
    try:
        # Ensure folder structure exists
        await _ensure_folder_structure(client, note.folder)

        note_path = get_note_path(note.folder, note.filename)

        # Check if file already exists
        try:
            await client.get_item_by_path(note_path)
            raise HTTPException(status_code=409, detail="Note already exists")
        except Exception as e:
            if "itemNotFound" not in str(e):
                raise

        # Upload the file
        result = await client.upload_file(note_path, note.content.encode("utf-8"))

        # Ingest into vector store (non-blocking - note is created even if this fails)
        indexed = False
        try:
            await ingest_document(
                content=note.content,
                source_path=note_path,
                metadata={"folder": note.folder, "filename": note.filename},
            )
            indexed = True
        except Exception as e:
            logger.warning(f"Failed to index note {note_path}: {e}")

        return {
            "success": True,
            "path": note_path,
            "id": result.get("id"),
            "indexed": indexed,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=safe_error_message(e, "Create note")
        ) from e


@router.put("/update/{folder}/{filename:path}")
async def update_note(
    folder: str,
    filename: str,
    note: NoteUpdate,
    client: GraphClient = Depends(get_graph_client),
):
    """Update an existing note."""
    _validate_path_component(folder, "folder")
    _validate_path_component(filename, "filename")
    try:
        note_path = get_note_path(folder, filename)

        # Upload the updated content
        result = await client.upload_file(note_path, note.content.encode("utf-8"))

        # Re-ingest into vector store (non-blocking)
        indexed = False
        try:
            await ingest_document(
                content=note.content,
                source_path=note_path,
                metadata={"folder": folder, "filename": filename},
            )
            indexed = True
        except Exception as e:
            logger.warning(f"Failed to re-index note {note_path}: {e}")

        return {
            "success": True,
            "path": note_path,
            "id": result.get("id"),
            "indexed": indexed,
        }
    except Exception as e:
        if "itemNotFound" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(
            status_code=500, detail=safe_error_message(e, "Update note")
        ) from e


@router.delete("/delete/{folder}/{filename:path}")
async def delete_note(
    folder: str,
    filename: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Delete a note."""
    _validate_path_component(folder, "folder")
    _validate_path_component(filename, "filename")
    try:
        note_path = get_note_path(folder, filename)

        await client.delete_item(note_path)
        await delete_document(note_path)

        return {"success": True, "deleted": note_path}
    except Exception as e:
        if "itemNotFound" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(
            status_code=500, detail=safe_error_message(e, "Delete note")
        ) from e


@router.post("/diary/today")
async def create_today_diary(
    client: GraphClient = Depends(get_graph_client),
):
    """Create or get today's diary entry."""
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}.md"

    try:
        # Check if today's entry exists
        note_path = get_note_path("Diary", filename)
        content = await client.get_file_content(note_path)

        return {
            "exists": True,
            "filename": filename,
            "content": content.decode("utf-8"),
        }
    except Exception as e:
        if "itemNotFound" in str(e):
            # Create new diary entry
            template = f"""# {today}

## Morning

## Tasks for Today
- [ ]

## Notes

## Evening Reflection

"""
            await _ensure_folder_structure(client, "Diary")
            await client.upload_file(note_path, template.encode("utf-8"))

            # Index in vector store (non-blocking)
            indexed = False
            try:
                await ingest_document(
                    content=template,
                    source_path=note_path,
                    metadata={"folder": "Diary", "filename": filename, "type": "diary"},
                )
                indexed = True
            except Exception as e:
                logger.warning(f"Failed to index diary entry {note_path}: {e}")

            return {
                "exists": False,
                "created": True,
                "filename": filename,
                "content": template,
                "indexed": indexed,
            }

        raise HTTPException(
            status_code=500, detail=safe_error_message(e, "Create diary entry")
        ) from e


async def _ensure_folder_structure(client: GraphClient, specific_folder: str | None = None):
    """Ensure the PersonalAI folder structure exists."""
    base = settings.onedrive_base_folder
    folders = [specific_folder] if specific_folder else ["Diary", "Projects", "Study", "Inbox", "_system"]

    # Create base folder
    try:
        await client.get_item_by_path(base)
    except Exception:
        with contextlib.suppress(Exception):
            await client.create_folder("", base)

    # Create subfolders
    for folder in folders:
        try:
            await client.get_item_by_path(f"{base}/{folder}")
        except Exception:
            with contextlib.suppress(Exception):
                await client.create_folder(base, folder)


@router.post("/init")
async def initialize_folders(client: GraphClient = Depends(get_graph_client)):
    """Initialize the PersonalAI folder structure in OneDrive."""
    await _ensure_folder_structure(client)
    return {
        "status": "initialized",
        "folders": ["Diary", "Projects", "Study", "Inbox", "_system"],
    }
