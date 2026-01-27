"""Microsoft OAuth authentication using MSAL with multi-account support."""

import json
import logging
import secrets

import msal
from .config import get_settings
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

# Redis client (initialized lazily)
_redis_client = None


def _get_redis():
    """Get Redis client, initializing if needed."""
    global _redis_client
    if _redis_client is None:
        redis_url = getattr(settings, "redis_url", None)
        if redis_url:
            try:
                import redis
                _redis_client = redis.from_url(redis_url, decode_responses=True)
                _redis_client.ping()  # Test connection
                logger.info("Connected to Redis for token storage")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory storage: {e}")
                _redis_client = False  # Mark as failed, don't retry
        else:
            _redis_client = False  # No Redis URL configured
    return _redis_client if _redis_client else None

# Account purposes
ACCOUNT_PURPOSE_PRIMARY = "primary"  # All services (default)
ACCOUNT_PURPOSE_EMAIL = "email"  # Email + Calendar only
ACCOUNT_PURPOSE_STORAGE = "storage"  # OneDrive + To Do only

# Scopes by purpose
SCOPES_BY_PURPOSE = {
    ACCOUNT_PURPOSE_PRIMARY: [
        "User.Read",
        "Files.ReadWrite.All",
        "Tasks.ReadWrite",
        "Calendars.ReadWrite",
        "Mail.Read",
    ],
    ACCOUNT_PURPOSE_EMAIL: [
        "User.Read",
        "Calendars.ReadWrite",
        "Mail.Read",
    ],
    ACCOUNT_PURPOSE_STORAGE: [
        "User.Read",
        "Files.ReadWrite.All",
        "Tasks.ReadWrite",
    ],
}

# In-memory token cache (fallback when Redis unavailable)
_token_cache: dict[str, dict[str, dict]] = {}  # {session_id: {purpose: {token_data, user_info}}}
_state_cache: dict[str, dict] = {}  # {state: {purpose: str}}

# Token expiry: 7 days in seconds
TOKEN_EXPIRY = 86400 * 7


def _get_session_data(session_id: str) -> dict | None:
    """Get session data from Redis or memory."""
    redis = _get_redis()
    if redis:
        data = redis.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None
    return _token_cache.get(session_id)


def _set_session_data(session_id: str, data: dict):
    """Store session data in Redis or memory."""
    redis = _get_redis()
    if redis:
        redis.setex(f"session:{session_id}", TOKEN_EXPIRY, json.dumps(data))
    else:
        _token_cache[session_id] = data


def _delete_session_data(session_id: str):
    """Delete session data from Redis or memory."""
    redis = _get_redis()
    if redis:
        redis.delete(f"session:{session_id}")
    elif session_id in _token_cache:
        del _token_cache[session_id]


def _get_msal_app() -> msal.ConfidentialClientApplication:
    """Create MSAL confidential client application."""
    authority = f"https://login.microsoftonline.com/{settings.azure_tenant_id}"

    return msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=authority,
    )


def _build_auth_url(state: str, purpose: str = ACCOUNT_PURPOSE_PRIMARY) -> str:
    """Build the Microsoft OAuth authorization URL."""
    app = _get_msal_app()
    scopes = SCOPES_BY_PURPOSE.get(purpose, SCOPES_BY_PURPOSE[ACCOUNT_PURPOSE_PRIMARY])

    # Use prompt=select_account to force account selection
    return app.get_authorization_request_url(
        scopes=scopes,
        state=state,
        redirect_uri=settings.azure_redirect_uri,
        prompt="select_account",  # Always show account picker
    )


def get_token_from_cache(session_id: str, purpose: str | None = None) -> dict | None:
    """Get access token from cache for a specific purpose."""
    session_data = _get_session_data(session_id)
    if not session_data:
        return None

    # If purpose specified, get that specific account
    if purpose and purpose in session_data:
        return session_data[purpose].get("token_data")

    # Otherwise return primary or first available
    if ACCOUNT_PURPOSE_PRIMARY in session_data:
        return session_data[ACCOUNT_PURPOSE_PRIMARY].get("token_data")

    # Return first available
    for p in session_data:
        if "token_data" in session_data[p]:
            return session_data[p]["token_data"]

    return None


def get_access_token(session_id: str, purpose: str | None = None) -> str | None:
    """Get access token string for a specific purpose."""
    token_data = get_token_from_cache(session_id, purpose)
    if token_data:
        return token_data.get("access_token")
    return None


def get_access_token_for_service(session_id: str, service: str) -> str | None:
    """Get the appropriate access token for a service.

    Services: 'email', 'calendar', 'notes', 'tasks'
    """
    session_data = _get_session_data(session_id)
    if not session_data:
        return None

    # Map services to purposes
    if service in ("email", "calendar"):
        # Prefer email account, fall back to primary
        for purpose in [ACCOUNT_PURPOSE_EMAIL, ACCOUNT_PURPOSE_PRIMARY]:
            if purpose in session_data:
                return session_data[purpose].get("token_data", {}).get("access_token")
    elif service in ("notes", "tasks"):
        # Prefer storage account, fall back to primary
        for purpose in [ACCOUNT_PURPOSE_STORAGE, ACCOUNT_PURPOSE_PRIMARY]:
            if purpose in session_data:
                return session_data[purpose].get("token_data", {}).get("access_token")

    # Fall back to any available token
    return get_access_token(session_id)


@router.get("/login")
async def login(request: Request, purpose: str = ACCOUNT_PURPOSE_PRIMARY):
    """Initiate Microsoft OAuth login flow.

    Args:
        purpose: Account purpose - 'primary', 'email', or 'storage'
    """
    if purpose not in SCOPES_BY_PURPOSE:
        purpose = ACCOUNT_PURPOSE_PRIMARY

    state = secrets.token_urlsafe(32)
    _state_cache[state] = {"purpose": purpose}

    # Check if user already has a session (adding another account)
    session_id = request.cookies.get("session_id")
    if session_id:
        _state_cache[state]["existing_session"] = session_id

    auth_url = _build_auth_url(state, purpose)
    return RedirectResponse(url=auth_url)


@router.get("/login/email")
async def login_email(request: Request):
    """Add an email/calendar account."""
    return await login(request, purpose=ACCOUNT_PURPOSE_EMAIL)


@router.get("/login/storage")
async def login_storage(request: Request):
    """Add a storage/tasks account (OneDrive + To Do)."""
    return await login(request, purpose=ACCOUNT_PURPOSE_STORAGE)


@router.get("/callback")
async def auth_callback(
    _request: Request,  # Required by FastAPI but unused
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """Handle OAuth callback from Microsoft."""
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Authentication error: {error} - {error_description}",
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    # Verify state
    if state not in _state_cache:
        raise HTTPException(status_code=400, detail="Invalid state")

    state_data = _state_cache.pop(state)
    purpose = state_data.get("purpose", ACCOUNT_PURPOSE_PRIMARY)
    existing_session = state_data.get("existing_session")

    # Exchange code for token
    app = _get_msal_app()
    scopes = SCOPES_BY_PURPOSE.get(purpose, SCOPES_BY_PURPOSE[ACCOUNT_PURPOSE_PRIMARY])

    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=scopes,
        redirect_uri=settings.azure_redirect_uri,
    )

    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=f"Token error: {result.get('error_description', result.get('error'))}",
        )

    # Extract user info
    claims = result.get("id_token_claims", {})
    user_info = {
        "name": claims.get("name", "Unknown"),
        "email": claims.get("preferred_username", claims.get("email", "Unknown")),
    }

    # Use existing session or create new one
    existing_data = _get_session_data(existing_session) if existing_session else None
    if existing_session and existing_data:
        session_id = existing_session
        session_data = existing_data
    else:
        session_id = secrets.token_urlsafe(32)
        session_data = {}

    # Store token under the purpose key
    session_data[purpose] = {
        "token_data": result,
        "user_info": user_info,
    }
    _set_session_data(session_id, session_data)

    # Redirect to frontend with session cookie
    response = RedirectResponse(url=settings.frontend_url)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=not settings.debug,  # Secure in production (HTTPS)
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    return response


@router.get("/logout")
async def logout(request: Request, response: Response, purpose: str | None = None):
    """Log out - all accounts or a specific one.

    Args:
        purpose: If provided, only log out this account type. Otherwise log out all.
    """
    session_id = request.cookies.get("session_id")
    session_data = _get_session_data(session_id) if session_id else None

    if session_id and session_data:
        if purpose and purpose in session_data:
            # Remove just this account
            del session_data[purpose]
            # If no accounts left, delete session
            if not session_data:
                _delete_session_data(session_id)
                response = RedirectResponse(url=settings.frontend_url)
                response.delete_cookie("session_id")
                return response
            _set_session_data(session_id, session_data)
            return RedirectResponse(url=settings.frontend_url)
        else:
            # Remove all accounts
            _delete_session_data(session_id)

    response = RedirectResponse(url=settings.frontend_url)
    response.delete_cookie("session_id")

    return response


@router.get("/me")
async def get_current_user(request: Request):
    """Get current user info (primary account)."""
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_data = _get_session_data(session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session expired")

    # Get primary user or first available
    for purpose in [ACCOUNT_PURPOSE_PRIMARY, ACCOUNT_PURPOSE_EMAIL, ACCOUNT_PURPOSE_STORAGE]:
        if purpose in session_data:
            user_info = session_data[purpose].get("user_info", {})
            return {
                "authenticated": True,
                "name": user_info.get("name", "Unknown"),
                "email": user_info.get("email", "Unknown"),
            }

    raise HTTPException(status_code=401, detail="No accounts configured")


@router.get("/accounts")
async def get_accounts(request: Request):
    """Get all connected accounts."""
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_data = _get_session_data(session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session expired")

    accounts = []

    purpose_labels = {
        ACCOUNT_PURPOSE_PRIMARY: "Primary (All Services)",
        ACCOUNT_PURPOSE_EMAIL: "Email & Calendar",
        ACCOUNT_PURPOSE_STORAGE: "Notes & Tasks",
    }

    for purpose, data in session_data.items():
        user_info = data.get("user_info", {})
        accounts.append(
            {
                "purpose": purpose,
                "label": purpose_labels.get(purpose, purpose),
                "name": user_info.get("name", "Unknown"),
                "email": user_info.get("email", "Unknown"),
            }
        )

    return {
        "authenticated": True,
        "accounts": accounts,
        "has_email_account": ACCOUNT_PURPOSE_EMAIL in session_data
        or ACCOUNT_PURPOSE_PRIMARY in session_data,
        "has_storage_account": ACCOUNT_PURPOSE_STORAGE in session_data
        or ACCOUNT_PURPOSE_PRIMARY in session_data,
    }
