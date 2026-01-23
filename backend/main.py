"""Personal AI Assistant - FastAPI Backend."""

import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from .auth import router as auth_router
from .config import get_settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .routers.actions import router as actions_router
from .routers.arxiv import router as arxiv_router
from .routers.calendar import router as calendar_router
from .routers.chat import router as chat_router
from .routers.email import router as email_router
from .routers.github import router as github_router
from .routers.notes import router as notes_router
from .routers.onenote import router as onenote_router
from .routers.sync import router as sync_router
from .routers.tasks import router as tasks_router
from .routers.telegram import router as telegram_router
from .services.arxiv import get_arxiv_scheduler
from .services.security import SecurityEventType, log_security_event

settings = get_settings()

# Simple in-memory rate limiter (use Redis for production with multiple workers)
_request_counts: dict[str, list[datetime]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 60  # requests per window
RATE_LIMIT_WINDOW = timedelta(minutes=1)


@asynccontextmanager
async def lifespan(_app: FastAPI):  # Required by FastAPI lifespan protocol
    """Application lifespan handler."""
    # Startup
    print(f"Starting {settings.app_name}...")

    # Start ArXiv digest scheduler (runs daily)
    arxiv_scheduler = get_arxiv_scheduler()
    arxiv_scheduler.start()

    yield

    # Shutdown
    print("Shutting down...")
    arxiv_scheduler.stop()


app = FastAPI(
    title=settings.app_name,
    description="Personal AI Assistant with notes, tasks, and calendar integration",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware."""
    # Only rate limit chat endpoints which are most expensive
    if not request.url.path.startswith("/chat/"):
        return await call_next(request)

    session_id = request.cookies.get("session_id", "anonymous")
    now = datetime.utcnow()

    # Clean old entries
    _request_counts[session_id] = [
        t for t in _request_counts[session_id] if now - t < RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(_request_counts[session_id]) >= RATE_LIMIT_REQUESTS:
        log_security_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            session_id,
            {"path": request.url.path, "count": len(_request_counts[session_id])},
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait before trying again."},
        )

    _request_counts[session_id].append(now)
    return await call_next(request)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api")
async def api_info():
    """API info endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


# Include routers - MUST be before catch-all SPA route
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(notes_router)
app.include_router(onenote_router)
app.include_router(tasks_router)
app.include_router(calendar_router)
app.include_router(email_router)
app.include_router(telegram_router)
app.include_router(github_router)
app.include_router(sync_router)
app.include_router(actions_router)
app.include_router(arxiv_router)


# Serve frontend static files in production
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    # Serve static assets (js, css, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        # Check if it's a static file
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint when no frontend is available."""
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "status": "running",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
