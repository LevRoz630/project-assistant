"""Configuration settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App
    app_name: str = "Personal AI Assistant"
    debug: bool = False
    secret_key: str = ""  # Required in production - set via SECRET_KEY env var

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
    google_api_key: str = ""  # Gemini API key from https://makersuite.google.com/app/apikey
    default_llm_provider: str = "anthropic"  # "anthropic", "openai", or "google"
    default_model: str = "claude-sonnet-4-20250514"

    # OneDrive paths
    onedrive_base_folder: str = "PersonalAI"

    # ChromaDB / Embeddings
    chroma_persist_directory: str = "./data/chroma"
    embedding_provider: str = "huggingface"  # "huggingface", "openai", "google", or "auto"

    # Telegram (get API credentials from https://my.telegram.org)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_phone: str = ""  # Your phone number with country code
    telegram_session_path: str = "./data/telegram_session"

    # GitHub (get token from https://github.com/settings/tokens)
    github_token: str = ""
    github_username: str = ""  # Optional, for filtering

    # Web Search & Fetch
    enable_web_search: bool = True  # Enable AI to search the web
    enable_url_fetch: bool = True  # Enable AI to fetch and read webpage content

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # Redis (for persistent token storage)
    redis_url: str = ""  # e.g., redis://localhost:6379 or Railway Redis URL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()

    # Validate SECRET_KEY is set in production
    if not settings.secret_key:
        if settings.debug:
            # Allow empty secret in debug mode with a warning
            import warnings
            settings.secret_key = "debug-only-insecure-key"
            warnings.warn(
                "SECRET_KEY not set - using insecure default. "
                "Set SECRET_KEY environment variable for production.",
                UserWarning,
                stacklevel=2,
            )
        else:
            raise ValueError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )

    return settings
