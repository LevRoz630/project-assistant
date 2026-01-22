"""Sync endpoints for auto-indexing."""

from auth import get_access_token
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from services.sync import (
    get_scheduler,
    get_sync_state,
    sync_notes_to_vectors,
)

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncSettings(BaseModel):
    """Settings for sync scheduler."""

    enabled: bool = True
    interval_minutes: int = 5


@router.get("/status")
async def get_sync_status(request: Request):
    """Get the current sync status."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    state = get_sync_state()
    scheduler = get_scheduler()

    return {
        "last_sync": state.last_sync.isoformat() if state.last_sync else None,
        "is_syncing": state.is_syncing,
        "indexed_files_count": len(state.indexed_files),
        "scheduler_running": scheduler.is_running,
        "recent_errors": state.errors[-5:] if state.errors else [],
    }


@router.post("/now")
async def sync_now(request: Request, background_tasks: BackgroundTasks, force_full: bool = False):
    """Trigger an immediate sync."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    state = get_sync_state()
    if state.is_syncing:
        return {"status": "already_syncing"}

    # Run sync in background for faster response
    background_tasks.add_task(sync_notes_to_vectors, token, force_full)

    return {"status": "sync_started", "force_full": force_full}


@router.post("/scheduler/start")
async def start_scheduler(request: Request, settings: SyncSettings | None = None):
    """Start the background sync scheduler."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    scheduler = get_scheduler()
    interval = settings.interval_minutes if settings else 5

    scheduler.start(token, interval)

    return {"status": "started", "interval_minutes": interval}


@router.post("/scheduler/stop")
async def stop_scheduler(request: Request):
    """Stop the background sync scheduler."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    scheduler = get_scheduler()
    scheduler.stop()

    return {"status": "stopped"}


@router.get("/indexed-files")
async def get_indexed_files(request: Request):
    """Get list of indexed files."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    state = get_sync_state()

    return {
        "count": len(state.indexed_files),
        "files": list(state.indexed_files.keys()),
    }
