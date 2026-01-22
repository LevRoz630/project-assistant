"""Personal AI Assistant - FastAPI Backend."""

from contextlib import asynccontextmanager

from auth import router as auth_router
from config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.actions import router as actions_router
from routers.calendar import router as calendar_router
from routers.chat import router as chat_router
from routers.email import router as email_router
from routers.notes import router as notes_router
from routers.sync import router as sync_router
from routers.tasks import router as tasks_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):  # Required by FastAPI lifespan protocol
    """Application lifespan handler."""
    # Startup
    print(f"Starting {settings.app_name}...")
    yield
    # Shutdown
    print("Shutting down...")


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
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(notes_router)
app.include_router(tasks_router)
app.include_router(calendar_router)
app.include_router(email_router)
app.include_router(sync_router)
app.include_router(actions_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
