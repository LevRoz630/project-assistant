"""Notes CRUD endpoints - OneDrive integration."""

import contextlib
from datetime import datetime

from auth import get_access_token_for_service
from config import get_settings
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from services.graph import GraphClient
from services.vectors import delete_document, ingest_document

router = APIRouter(prefix="/notes", tags=["notes"])
settings = get_settings()


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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list/{folder}")
async def list_notes(folder: str, client: GraphClient = Depends(get_graph_client)):
    """List all notes in a folder."""
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/content/{folder}/{filename:path}")
async def get_note(
    folder: str,
    filename: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Get the content of a note."""
    try:
        note_path = get_note_path(folder, filename)
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
        if "itemNotFound" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/create")
async def create_note(
    note: NoteCreate,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a new note."""
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

        # Ingest into vector store
        await ingest_document(
            content=note.content,
            source_path=note_path,
            metadata={"folder": note.folder, "filename": note.filename},
        )

        return {
            "success": True,
            "path": note_path,
            "id": result.get("id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/update/{folder}/{filename:path}")
async def update_note(
    folder: str,
    filename: str,
    note: NoteUpdate,
    client: GraphClient = Depends(get_graph_client),
):
    """Update an existing note."""
    try:
        note_path = get_note_path(folder, filename)

        # Upload the updated content
        result = await client.upload_file(note_path, note.content.encode("utf-8"))

        # Re-ingest into vector store
        await ingest_document(
            content=note.content,
            source_path=note_path,
            metadata={"folder": folder, "filename": filename},
        )

        return {
            "success": True,
            "path": note_path,
            "id": result.get("id"),
        }
    except Exception as e:
        if "itemNotFound" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/delete/{folder}/{filename:path}")
async def delete_note(
    folder: str,
    filename: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Delete a note."""
    try:
        note_path = get_note_path(folder, filename)

        await client.delete_item(note_path)
        await delete_document(note_path)

        return {"success": True, "deleted": note_path}
    except Exception as e:
        if "itemNotFound" in str(e):
            raise HTTPException(status_code=404, detail="Note not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


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

            await ingest_document(
                content=template,
                source_path=note_path,
                metadata={"folder": "Diary", "filename": filename, "type": "diary"},
            )

            return {
                "exists": False,
                "created": True,
                "filename": filename,
                "content": template,
            }

        raise HTTPException(status_code=500, detail=str(e)) from e


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
