"""OneDrive sync service for automatic RAG indexing."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from config import get_settings

from services.graph import GraphClient
from services.vectors import delete_document, ingest_document

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SyncState:
    """Tracks synchronization state."""

    delta_link: str | None = None
    last_sync: datetime | None = None
    is_syncing: bool = False
    indexed_files: dict = field(default_factory=dict)  # path -> last_modified
    errors: list = field(default_factory=list)


# Global sync state (in production, use Redis or database)
_sync_state = SyncState()


def get_sync_state() -> SyncState:
    """Get the current sync state."""
    return _sync_state


async def sync_notes_to_vectors(access_token: str, force_full: bool = False) -> dict:
    """
    Sync notes from OneDrive to vector store.

    Uses OneDrive delta queries for efficient incremental sync.
    """
    state = get_sync_state()

    if state.is_syncing:
        return {"status": "already_syncing"}

    state.is_syncing = True
    state.errors = []

    client = GraphClient(access_token)
    stats = {"added": 0, "updated": 0, "deleted": 0, "errors": []}

    try:
        if force_full or not state.delta_link:
            # Full sync - get all files
            stats = await _full_sync(client)
        else:
            # Incremental sync using delta
            stats = await _delta_sync(client, state.delta_link)

        state.last_sync = datetime.now()

    except Exception as e:
        logger.error(f"Sync error: {e}")
        stats["errors"].append(str(e))
    finally:
        state.is_syncing = False

    return {
        "status": "completed",
        "stats": stats,
        "last_sync": state.last_sync.isoformat() if state.last_sync else None,
    }


async def _full_sync(client: GraphClient) -> dict:
    """Perform a full sync of all notes."""
    state = get_sync_state()
    stats = {"added": 0, "updated": 0, "deleted": 0, "errors": []}

    base_folder = settings.onedrive_base_folder

    try:
        # Get all folders
        folders_result = await client.list_folder(base_folder)
        # Skip system/hidden folders (.obsidian, _system, etc.)
        folders = [
            item["name"]
            for item in folders_result.get("value", [])
            if "folder" in item and not item["name"].startswith("_") and not item["name"].startswith(".")
        ]
    except Exception as e:
        stats["errors"].append(f"Failed to list folders: {e}")
        return stats

    new_indexed_files = {}

    # Process each folder
    for folder in folders:
        folder_path = f"{base_folder}/{folder}"

        try:
            notes_result = await client.list_folder(folder_path)

            for item in notes_result.get("value", []):
                if "file" not in item or not item["name"].endswith(".md"):
                    continue

                note_path = f"{folder_path}/{item['name']}"
                last_modified = item.get("lastModifiedDateTime", "")

                # Check if file needs indexing
                if (
                    note_path in state.indexed_files
                    and state.indexed_files[note_path] == last_modified
                ):
                    new_indexed_files[note_path] = last_modified
                    continue

                try:
                    content = await client.get_file_content(note_path)
                    await ingest_document(
                        content=content.decode("utf-8"),
                        source_path=note_path,
                        metadata={"folder": folder, "filename": item["name"]},
                    )

                    if note_path in state.indexed_files:
                        stats["updated"] += 1
                    else:
                        stats["added"] += 1

                    new_indexed_files[note_path] = last_modified

                except Exception as e:
                    stats["errors"].append(f"{note_path}: {e}")

        except Exception as e:
            stats["errors"].append(f"Folder {folder}: {e}")

    # Find deleted files
    for old_path in state.indexed_files:
        if old_path not in new_indexed_files:
            try:
                await delete_document(old_path)
                stats["deleted"] += 1
            except Exception as e:
                stats["errors"].append(f"Delete {old_path}: {e}")

    state.indexed_files = new_indexed_files

    return stats


async def _delta_sync(client: GraphClient, _delta_link: str) -> dict:
    """Perform incremental sync using delta link."""
    # For now, fall back to full sync since delta queries require
    # tracking the drive item ID. Future enhancement: use delta API.
    # Microsoft Graph delta: /me/drive/root/delta

    return await _full_sync(client)


class SyncScheduler:
    """Background scheduler for periodic sync."""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._interval_minutes = 5
        self._access_token: str | None = None

    def start(self, access_token: str, interval_minutes: int = 5):
        """Start the background sync scheduler."""
        if self._running:
            return

        self._access_token = access_token
        self._interval_minutes = interval_minutes
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Sync scheduler started (interval: {interval_minutes} min)")

    def stop(self):
        """Stop the background sync scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Sync scheduler stopped")

    def update_token(self, access_token: str):
        """Update the access token for sync operations."""
        self._access_token = access_token

    @property
    def is_running(self) -> bool:
        return self._running

    async def _run_loop(self):
        """Background loop for periodic sync."""
        while self._running:
            try:
                await asyncio.sleep(self._interval_minutes * 60)

                if self._access_token and self._running:
                    logger.info("Running scheduled sync...")
                    result = await sync_notes_to_vectors(self._access_token)
                    logger.info(f"Sync completed: {result['stats']}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync scheduler error: {e}")


# Global scheduler instance
_scheduler = SyncScheduler()


def get_scheduler() -> SyncScheduler:
    """Get the global sync scheduler."""
    return _scheduler
