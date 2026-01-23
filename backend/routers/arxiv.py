"""ArXiv digest API endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..config import get_settings
from ..services.arxiv import (
    generate_digest,
    get_arxiv_scheduler,
    get_digest,
    get_digest_state,
    list_digests,
)

router = APIRouter(prefix="/arxiv", tags=["arxiv"])
settings = get_settings()


class ArxivConfig(BaseModel):
    """ArXiv digest configuration."""

    categories: list[str]
    interests: str
    schedule_hour: int
    max_papers: int
    top_n: int
    llm_provider: str


class ArxivConfigUpdate(BaseModel):
    """ArXiv digest configuration update (partial)."""

    categories: list[str] | None = None
    interests: str | None = None
    schedule_hour: int | None = None
    max_papers: int | None = None
    top_n: int | None = None
    llm_provider: str | None = None


@router.get("/digest")
async def get_latest_digest():
    """Get the most recent arXiv digest."""
    digest = get_digest()
    if not digest:
        return {
            "status": "no_digest",
            "message": "No digest available yet. Trigger a manual run or wait for scheduled generation.",
        }
    return digest


@router.get("/digest/{date}")
async def get_digest_by_date(date: str):
    """Get an arXiv digest for a specific date (YYYY-MM-DD format)."""
    digest = get_digest(date)
    if not digest:
        raise HTTPException(status_code=404, detail=f"No digest found for {date}")
    return digest


@router.get("/digests")
async def list_available_digests(limit: int = 30):
    """List available digest dates."""
    dates = list_digests(limit)
    return {"dates": dates, "count": len(dates)}


@router.get("/status")
async def get_status():
    """Get arXiv digest service status."""
    state = get_digest_state()
    scheduler = get_arxiv_scheduler()

    return {
        "is_generating": state.is_generating,
        "last_digest": state.last_digest.isoformat() if state.last_digest else None,
        "scheduler_running": scheduler.is_running,
        "errors": state.errors[-5:] if state.errors else [],  # Last 5 errors
    }


@router.post("/run-now")
async def run_digest_now(background_tasks: BackgroundTasks):
    """Trigger immediate digest generation (runs in background)."""
    state = get_digest_state()

    if state.is_generating:
        return {"status": "already_generating", "message": "A digest is currently being generated."}

    background_tasks.add_task(generate_digest)
    return {"status": "started", "message": "Digest generation started in background."}


@router.post("/scheduler/start")
async def start_scheduler(schedule_hour: int | None = None):
    """Start the background arXiv scheduler."""
    scheduler = get_arxiv_scheduler()

    if scheduler.is_running:
        return {"status": "already_running"}

    scheduler.start(schedule_hour)
    return {
        "status": "started",
        "message": f"Scheduler started. Will run daily at {schedule_hour or settings.arxiv_schedule_hour}:00 UTC.",
    }


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the background arXiv scheduler."""
    scheduler = get_arxiv_scheduler()

    if not scheduler.is_running:
        return {"status": "not_running"}

    scheduler.stop()
    return {"status": "stopped"}


@router.get("/config")
async def get_config():
    """Get current arXiv digest configuration."""
    return ArxivConfig(
        categories=settings.arxiv_categories,
        interests=settings.arxiv_interests,
        schedule_hour=settings.arxiv_schedule_hour,
        max_papers=settings.arxiv_max_papers,
        top_n=settings.arxiv_top_n,
        llm_provider=settings.arxiv_llm_provider,
    )


@router.put("/config")
async def update_config(config: ArxivConfigUpdate):
    """Update arXiv digest configuration.

    Note: Changes are applied at runtime but not persisted.
    For persistent changes, update environment variables.
    """
    # This applies runtime changes only - in production you'd
    # store these in a database or config file
    if config.categories is not None:
        settings.arxiv_categories = config.categories
    if config.interests is not None:
        settings.arxiv_interests = config.interests
    if config.schedule_hour is not None:
        settings.arxiv_schedule_hour = config.schedule_hour
    if config.max_papers is not None:
        settings.arxiv_max_papers = config.max_papers
    if config.top_n is not None:
        settings.arxiv_top_n = config.top_n
    if config.llm_provider is not None:
        settings.arxiv_llm_provider = config.llm_provider

    return {"status": "updated", "config": await get_config()}
