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


def _validate_path_component(value: str, field_name: str, is_filename: bool = False) -> str:
    """Validate a path component (folder or filename) to prevent path traversal attacks."""
    if not value:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_input", "message": f"{field_name} cannot be empty"}
        )

    # Reject path traversal attempts
    if ".." in value:
        raise HTTPException(
            status_code=400,
            detail={"code": "path_traversal", "message": f"Invalid {field_name}: path traversal not allowed"}
        )

    # Reject absolute paths
    if value.startswith("/") or value.startswith("\\"):
        raise HTTPException(
            status_code=400,
            detail={"code": "absolute_path", "message": f"Invalid {field_name}: absolute paths not allowed"}
        )

    # Reject paths containing slashes (except for filename:path which FastAPI handles)
    if "/" in value or "\\" in value:
        # Allow forward slashes in filenames since FastAPI's :path converter handles nested paths
        # But still reject backslashes and double slashes
        if "\\" in value or "//" in value:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_chars", "message": f"Invalid {field_name}: invalid path characters"}
            )

    # Reject null bytes
    if "\x00" in value:
        raise HTTPException(
            status_code=400,
            detail={"code": "null_byte", "message": f"Invalid {field_name}: null bytes not allowed"}
        )

    # Additional validation for filenames
    if is_filename:
        # Check max length (100 chars)
        if len(value) > 100:
            raise HTTPException(
                status_code=400,
                detail={"code": "name_too_long", "message": f"{field_name} is too long (max 100 characters)"}
            )

        # Check for invalid filename characters
        invalid_chars = r':*?"<>|'
        if any(c in value for c in invalid_chars):
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_chars", "message": f"Invalid {field_name}: contains invalid characters ({invalid_chars})"}
            )

        # Reject names starting with a dot (hidden files)
        if value.startswith("."):
            raise HTTPException(
                status_code=400,
                detail={"code": "hidden_file", "message": f"Invalid {field_name}: cannot start with a dot"}
            )

    return value


def _validate_folder_path(value: str, field_name: str = "folder") -> str:
    """Validate a multi-segment folder path like 'Projects/SubA/SubB'."""
    if not value:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_input", "message": f"{field_name} cannot be empty"}
        )
    segments = value.split("/")
    if len(segments) > 6:
        raise HTTPException(
            status_code=400,
            detail={"code": "path_too_deep", "message": f"Invalid {field_name}: path too deep (max 6 levels)"}
        )
    for segment in segments:
        if not segment:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_input", "message": f"Invalid {field_name}: empty path segment"}
            )
        _validate_path_component(segment, field_name)
    return value


def _split_item_path(item_path: str) -> tuple[str, str]:
    """Split 'Projects/SubA/note.md' into ('Projects/SubA', 'note.md')."""
    if "/" not in item_path:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_path", "message": "Path must contain at least a folder and filename"}
        )
    folder, filename = item_path.rsplit("/", 1)
    return folder, filename


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

    folder: str  # e.g., "Diary", "Projects", "Projects/SubA"
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
        error_str = str(e).lower()
        if "itemnotfound" in error_str or "404" in error_str:
            await _ensure_folder_structure(client)
            return {"folders": ["Diary", "Projects", "Study", "Inbox"]}
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "List folders")}
        ) from e


@router.get("/list/{folder_path:path}")
async def list_notes(folder_path: str, client: GraphClient = Depends(get_graph_client)):
    """List all notes and subfolders in a folder."""
    _validate_folder_path(folder_path, "folder")
    try:
        full_path = f"{settings.onedrive_base_folder}/{folder_path}"
        result = await client.list_folder(full_path)

        notes = [
            {
                "name": item["name"],
                "id": item["id"],
                "path": f"{folder_path}/{item['name']}",
                "size": item.get("size", 0),
                "created": item.get("createdDateTime"),
                "modified": item.get("lastModifiedDateTime"),
            }
            for item in result.get("value", [])
            if "file" in item and item["name"].endswith(".md")
        ]

        subfolders = [
            {
                "name": item["name"],
                "path": f"{folder_path}/{item['name']}",
                "childCount": item.get("folder", {}).get("childCount", 0),
            }
            for item in result.get("value", [])
            if "folder" in item
            and not item["name"].startswith(".")
            and not item["name"].startswith("_")
        ]

        # Sort by modified date, newest first
        notes.sort(key=lambda x: x.get("modified", ""), reverse=True)
        subfolders.sort(key=lambda x: x["name"].lower())

        return {"folder": folder_path, "notes": notes, "subfolders": subfolders}
    except Exception as e:
        error_str = str(e).lower()
        if "itemnotfound" in error_str or "404" in error_str:
            return {"folder": folder_path, "notes": [], "subfolders": []}
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "List notes")}
        ) from e


@router.get("/content/{item_path:path}")
async def get_note(
    item_path: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Get the content of a note. Returns 404 if not found."""
    folder, filename = _split_item_path(item_path)
    _validate_folder_path(folder, "folder")
    _validate_path_component(filename, "filename", is_filename=True)
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
            raise HTTPException(
                status_code=404,
                detail={"code": "note_not_found", "message": f"Note '{filename}' not found in folder '{folder}'"}
            ) from e
        logger.error(f"Failed to load note {note_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "Load note")}
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
    _validate_folder_path(note.folder, "folder")
    _validate_path_component(note.filename, "filename", is_filename=True)

    # Auto-append .md extension if missing
    filename = note.filename if note.filename.endswith(".md") else f"{note.filename}.md"

    try:
        # Ensure folder structure exists
        logger.info(f"Creating note: folder={note.folder}, filename={filename}")
        try:
            await _ensure_folder_structure(client, note.folder)
        except Exception as e:
            logger.error(f"Failed to ensure folder structure: {type(e).__name__}: {e}")
            raise

        note_path = get_note_path(note.folder, filename)
        logger.info(f"Note path: {note_path}")

        # Check if file already exists
        try:
            await client.get_item_by_path(note_path)
            raise HTTPException(
                status_code=409,
                detail={"code": "already_exists", "message": f"Note '{filename}' already exists in folder '{note.folder}'"}
            )
        except HTTPException:
            raise
        except Exception as e:
            # 404 or itemNotFound means file doesn't exist - that's expected for new notes
            error_str = str(e).lower()
            if "itemnotfound" not in error_str and "404" not in error_str:
                logger.error(f"Error checking if file exists: {type(e).__name__}: {e}")
                raise

        # Upload the file
        logger.info(f"Uploading file to {note_path}")
        result = await client.upload_file(note_path, note.content.encode("utf-8"))

        # Ingest into vector store (non-blocking - note is created even if this fails)
        indexed = False
        try:
            await ingest_document(
                content=note.content,
                source_path=note_path,
                metadata={"folder": note.folder, "filename": filename},
            )
            indexed = True
        except Exception as e:
            logger.warning(f"Failed to index note {note_path}: {e}")

        return {
            "success": True,
            "path": note_path,
            "filename": filename,
            "id": result.get("id"),
            "indexed": indexed,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "Create note")}
        ) from e


@router.put("/update/{item_path:path}")
async def update_note(
    item_path: str,
    note: NoteUpdate,
    client: GraphClient = Depends(get_graph_client),
):
    """Update an existing note."""
    folder, filename = _split_item_path(item_path)
    _validate_folder_path(folder, "folder")
    _validate_path_component(filename, "filename", is_filename=True)
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
        error_str = str(e).lower()
        if "itemnotfound" in error_str or "404" in error_str:
            raise HTTPException(
                status_code=404,
                detail={"code": "note_not_found", "message": f"Note '{filename}' not found in folder '{folder}'"}
            ) from e
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "Update note")}
        ) from e


@router.delete("/delete/{item_path:path}")
async def delete_note(
    item_path: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Delete a note."""
    folder, filename = _split_item_path(item_path)
    _validate_folder_path(folder, "folder")
    _validate_path_component(filename, "filename", is_filename=True)
    try:
        note_path = get_note_path(folder, filename)

        await client.delete_item(note_path)
        await delete_document(note_path)

        return {"success": True, "deleted": note_path}
    except Exception as e:
        error_str = str(e).lower()
        if "itemnotfound" in error_str or "404" in error_str:
            raise HTTPException(
                status_code=404,
                detail={"code": "note_not_found", "message": f"Note '{filename}' not found"}
            ) from e
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "Delete note")}
        ) from e


class NoteMove(BaseModel):
    """Request body for moving a note."""

    target_folder: str


@router.post("/move/{item_path:path}")
async def move_note(
    item_path: str,
    move: NoteMove,
    client: GraphClient = Depends(get_graph_client),
):
    """Move a note to a different folder."""
    folder, filename = _split_item_path(item_path)
    _validate_folder_path(folder, "source folder")
    _validate_folder_path(move.target_folder, "target folder")
    _validate_path_component(filename, "filename", is_filename=True)

    if folder == move.target_folder:
        raise HTTPException(
            status_code=400,
            detail={"code": "same_folder", "message": "Note is already in that folder"}
        )

    source_path = get_note_path(folder, filename)
    target_folder_path = f"{settings.onedrive_base_folder}/{move.target_folder}"

    try:
        # Ensure target folder exists
        await _ensure_folder_structure(client, move.target_folder)

        # Move file in OneDrive
        result = await client.move_item(source_path, target_folder_path, filename)

        # Update vector store
        new_path = get_note_path(move.target_folder, filename)
        try:
            await delete_document(source_path)
            content = await client.get_file_content(new_path)
            await ingest_document(
                content=content.decode("utf-8"),
                source_path=new_path,
                metadata={"folder": move.target_folder, "filename": filename},
            )
        except Exception as e:
            logger.warning(f"Failed to update vector store after move: {e}")

        return {
            "success": True,
            "new_path": new_path,
            "new_folder": move.target_folder,
            "id": result.get("id"),
        }
    except Exception as e:
        error_str = str(e).lower()
        if "itemnotfound" in error_str or "404" in error_str:
            raise HTTPException(
                status_code=404,
                detail={"code": "note_not_found", "message": f"Note '{filename}' not found in folder '{folder}'"}
            ) from e
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "Move note")}
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
        error_str = str(e).lower()
        if "itemnotfound" in error_str or "404" in error_str:
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
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "Create diary entry")}
        ) from e


async def _ensure_folder_structure(client: GraphClient, specific_folder: str | None = None):
    """Ensure the PersonalAI folder structure exists. Handles nested paths like 'Projects/SubA/SubB'."""
    base = settings.onedrive_base_folder
    folders = [specific_folder] if specific_folder else ["Diary", "Projects", "Study", "Inbox", "_system"]

    # Create base folder
    try:
        await client.get_item_by_path(base)
    except Exception:
        with contextlib.suppress(Exception):
            await client.create_folder("", base)

    # Create subfolders, handling nested paths
    for folder in folders:
        segments = folder.split("/")
        current_path = base
        for segment in segments:
            next_path = f"{current_path}/{segment}"
            try:
                await client.get_item_by_path(next_path)
            except Exception:
                with contextlib.suppress(Exception):
                    await client.create_folder(current_path, segment)
            current_path = next_path


class FolderCreate(BaseModel):
    """Request body for creating a subfolder."""

    parent_path: str  # e.g., "Projects" or "Projects/SubA"
    name: str  # e.g., "SubB"


@router.post("/create-folder")
async def create_folder(
    body: FolderCreate,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a subfolder within the notes hierarchy."""
    _validate_folder_path(body.parent_path, "parent_path")
    _validate_path_component(body.name, "folder name")

    # Reject hidden/system folder names
    if body.name.startswith(".") or body.name.startswith("_"):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_name", "message": "Folder name cannot start with '.' or '_'"}
        )

    full_parent = f"{settings.onedrive_base_folder}/{body.parent_path}"
    new_path = f"{body.parent_path}/{body.name}"

    try:
        await client.create_folder(full_parent, body.name)
        return {"success": True, "name": body.name, "path": new_path}
    except Exception as e:
        error_str = str(e).lower()
        if "namealreadyexists" in error_str or "conflict" in error_str:
            raise HTTPException(
                status_code=409,
                detail={"code": "already_exists", "message": f"Folder '{body.name}' already exists"}
            ) from e
        if "itemnotfound" in error_str or "404" in error_str:
            raise HTTPException(
                status_code=404,
                detail={"code": "parent_not_found", "message": f"Parent folder '{body.parent_path}' not found"}
            ) from e
        raise HTTPException(
            status_code=500,
            detail={"code": "server_error", "message": safe_error_message(e, "Create folder")}
        ) from e


@router.get("/folder-tree")
async def get_folder_tree(client: GraphClient = Depends(get_graph_client)):
    """Get the full folder tree for the notes hierarchy (max depth 5)."""
    base = settings.onedrive_base_folder

    async def _scan_tree(path: str, depth: int) -> list[dict]:
        if depth > 5:
            return []
        try:
            result = await client.list_folder(path)
        except Exception:
            return []

        folders = []
        for item in result.get("value", []):
            if "folder" not in item:
                continue
            name = item["name"]
            if name.startswith(".") or name.startswith("_"):
                continue
            rel_path = f"{path}/{name}"
            # Strip the base folder prefix to get the relative path
            relative = rel_path[len(base) + 1:]
            children = await _scan_tree(rel_path, depth + 1)
            folders.append({"name": name, "path": relative, "children": children})
        folders.sort(key=lambda x: x["name"].lower())
        return folders

    tree = await _scan_tree(base, 0)
    return {"tree": tree}


@router.post("/init")
async def initialize_folders(client: GraphClient = Depends(get_graph_client)):
    """Initialize the PersonalAI folder structure in OneDrive."""
    await _ensure_folder_structure(client)
    return {
        "status": "initialized",
        "folders": ["Diary", "Projects", "Study", "Inbox", "_system"],
    }
