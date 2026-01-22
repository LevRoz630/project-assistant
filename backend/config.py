"""Configuration settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App
    app_name: str = "Personal AI Assistant"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Microsoft OAuth / Azure AD
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant_id: str = "common"  # "common" for personal accounts
    azure_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Microsoft Graph API scopes
    graph_scopes: list[str] = [
        "User.Read",
        "Files.ReadWrite.All",  # OneDrive
        "Tasks.ReadWrite",  # Microsoft To Do
        "Calendars.ReadWrite",  # Calendar
        "Mail.Read",  # Email (read only)
        "Notes.ReadWrite",  # OneNote
    ]

    # AI Configuration
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_llm_provider: str = "anthropic"  # "anthropic" or "openai"
    default_model: str = "claude-sonnet-4-20250514"

    # OneDrive paths
    onedrive_base_folder: str = "PersonalAI"

    # ChromaDB
    chroma_persist_directory: str = "./data/chroma"

    # Telegram (get API credentials from https://my.telegram.org)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_phone: str = ""  # Your phone number with country code
    telegram_session_path: str = "./data/telegram_session"

    # Frontend
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
