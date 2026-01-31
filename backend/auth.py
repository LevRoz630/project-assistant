"""Microsoft OAuth authentication using MSAL with multi-account support."""

import json
import logging
import secrets
import time

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
        "offline_access",  # Required for refresh tokens
        "User.Read",
        "Files.ReadWrite.All",
        "Tasks.ReadWrite",
        "Calendars.ReadWrite",
        "Mail.Read",
    ],
    ACCOUNT_PURPOSE_EMAIL: [
        "offline_access",
        "User.Read",
        "Calendars.ReadWrite",
        "Mail.Read",
    ],
    ACCOUNT_PURPOSE_STORAGE: [
        "offline_access",
        "User.Read",
        "Files.ReadWrite.All",
        "Tasks.ReadWrite",
    ],
}

# In-memory caches (fallback when Redis unavailable)
_token_cache: dict[str, dict[str, dict]] = {}  # {session_id: {purpose: {token_data, user_info}}}
_state_cache: dict[str, dict] = {}  # {state: {purpose: str, created_at: float, ip_hash: str}}

# OAuth state expiry (10 minutes)
STATE_EXPIRY_SECONDS = 600

# Token expiry: 7 days in seconds
TOKEN_EXPIRY = 86400 * 7

# Redis key prefixes
REDIS_SESSION_PREFIX = "session:"
REDIS_STATE_PREFIX = "oauth_state:"
REDIS_MSAL_CACHE_PREFIX = "msal_cache:"

# MSAL cache expiry: 30 days (refresh tokens last longer than access tokens)
MSAL_CACHE_EXPIRY = 86400 * 30


def _get_session_data(session_id: str) -> dict | None:
    """Get session data from Redis or memory."""
    redis = _get_redis()
    if redis:
        data = redis.get(f"{REDIS_SESSION_PREFIX}{session_id}")
        if data:
            return json.loads(data)
        return None
    return _token_cache.get(session_id)


def _set_session_data(session_id: str, data: dict):
    """Store session data in Redis or memory."""
    redis = _get_redis()
    if redis:
        redis.setex(f"{REDIS_SESSION_PREFIX}{session_id}", TOKEN_EXPIRY, json.dumps(data))
    else:
        _token_cache[session_id] = data


def _delete_session_data(session_id: str):
    """Delete session data from Redis or memory."""
    redis = _get_redis()
    if redis:
        redis.delete(f"{REDIS_SESSION_PREFIX}{session_id}")
    elif session_id in _token_cache:
        del _token_cache[session_id]


def _get_state_data(state: str) -> dict | None:
    """Get OAuth state data from Redis or memory."""
    redis = _get_redis()
    if redis:
        data = redis.get(f"{REDIS_STATE_PREFIX}{state}")
        if data:
            return json.loads(data)
        return None
    return _state_cache.get(state)


def _set_state_data(state: str, data: dict):
    """Store OAuth state data in Redis or memory.

    Redis: Uses TTL for automatic expiry.
    Memory: Requires manual cleanup via _cleanup_expired_states().
    """
    redis = _get_redis()
    if redis:
        redis.setex(f"{REDIS_STATE_PREFIX}{state}", STATE_EXPIRY_SECONDS, json.dumps(data))
    else:
        _state_cache[state] = data


def _delete_state_data(state: str):
    """Delete OAuth state data from Redis or memory."""
    redis = _get_redis()
    if redis:
        redis.delete(f"{REDIS_STATE_PREFIX}{state}")
    elif state in _state_cache:
        del _state_cache[state]


def _get_msal_cache(session_id: str, purpose: str) -> msal.SerializableTokenCache:
    """Get MSAL token cache from Redis or create new one."""
    cache = msal.SerializableTokenCache()
    redis = _get_redis()
    if redis:
        cache_key = f"{REDIS_MSAL_CACHE_PREFIX}{session_id}:{purpose}"
        cache_data = redis.get(cache_key)
        if cache_data:
            cache.deserialize(cache_data)
    return cache


def _save_msal_cache(session_id: str, purpose: str, cache: msal.SerializableTokenCache):
    """Save MSAL token cache to Redis if changed."""
    if cache.has_state_changed:
        redis = _get_redis()
        if redis:
            cache_key = f"{REDIS_MSAL_CACHE_PREFIX}{session_id}:{purpose}"
            redis.setex(cache_key, MSAL_CACHE_EXPIRY, cache.serialize())


def _delete_msal_cache(session_id: str, purpose: str):
    """Delete MSAL token cache from Redis."""
    redis = _get_redis()
    if redis:
        cache_key = f"{REDIS_MSAL_CACHE_PREFIX}{session_id}:{purpose}"
        redis.delete(cache_key)


def _get_msal_app_with_cache(
    session_id: str, purpose: str
) -> tuple[msal.ConfidentialClientApplication, msal.SerializableTokenCache]:
    """Create MSAL app with session-specific token cache for refresh support."""
    cache = _get_msal_cache(session_id, purpose)
    authority = f"https://login.microsoftonline.com/{settings.azure_tenant_id}"

    app = msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=authority,
        token_cache=cache,
    )
    return app, cache


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


def _is_token_expired(token_data: dict) -> bool:
    """Check if a token is expired or about to expire (5 min buffer)."""
    expires_on = token_data.get("expires_on")
    if not expires_on:
        # No expiry info - assume expired to force refresh/re-auth
        return True
    # Check with 5-minute buffer
    return time.time() > (expires_on - 300)


def _try_refresh_token(session_id: str, purpose: str) -> dict | None:
    """Attempt to refresh an expired token using MSAL.

    Returns new token_data if successful, None if refresh failed.
    """
    app, cache = _get_msal_app_with_cache(session_id, purpose)
    scopes = SCOPES_BY_PURPOSE.get(purpose, SCOPES_BY_PURPOSE[ACCOUNT_PURPOSE_PRIMARY])

    accounts = app.get_accounts()
    if not accounts:
        logger.warning(f"No accounts in MSAL cache for refresh: {session_id[:8]}...")
        return None

    # Try silent acquisition (uses refresh token automatically)
    result = app.acquire_token_silent(scopes, account=accounts[0])

    if result and "access_token" in result:
        # Calculate absolute expiry time
        if "expires_in" in result and "expires_on" not in result:
            result["expires_on"] = time.time() + result["expires_in"]

        # Save updated MSAL cache
        _save_msal_cache(session_id, purpose, cache)

        # Update session data with new token
        session_data = _get_session_data(session_id)
        if session_data and purpose in session_data:
            session_data[purpose]["token_data"] = result
            _set_session_data(session_id, session_data)

        logger.info(f"Successfully refreshed token for session {session_id[:8]}...")
        return result

    error_desc = result.get("error_description", "Unknown error") if result else "No result"
    logger.warning(f"Token refresh failed for session {session_id[:8]}...: {error_desc}")
    return None


def get_access_token(session_id: str, purpose: str | None = None) -> str | None:
    """Get access token string for a specific purpose.

    Returns None if token is expired or not found.
    """
    token_data = get_token_from_cache(session_id, purpose)
    if token_data:
        # Check if token is expired
        if _is_token_expired(token_data):
            logger.warning(f"Token expired for session {session_id[:8]}...")
            return None
        return token_data.get("access_token")
    return None


def get_access_token_for_service(session_id: str, service: str) -> str | None:
    """Get the appropriate access token for a service.

    Services: 'email', 'calendar', 'notes', 'tasks'
    Attempts to refresh expired tokens automatically.
    Returns None if token unavailable and refresh failed.
    """
    session_data = _get_session_data(session_id)
    if not session_data:
        return None

    # Map services to account purposes (in priority order)
    if service in ("email", "calendar"):
        purposes = [ACCOUNT_PURPOSE_EMAIL, ACCOUNT_PURPOSE_PRIMARY]
    elif service in ("notes", "tasks"):
        purposes = [ACCOUNT_PURPOSE_STORAGE, ACCOUNT_PURPOSE_PRIMARY]
    else:
        purposes = [ACCOUNT_PURPOSE_PRIMARY]

    for purpose in purposes:
        if purpose in session_data:
            token_data = session_data[purpose].get("token_data", {})

            if not token_data:
                continue

            # Check if token is still valid
            if not _is_token_expired(token_data):
                return token_data.get("access_token")

            # Token expired - try to refresh
            logger.info(f"Token expired for {purpose}, attempting refresh...")
            new_token_data = _try_refresh_token(session_id, purpose)
            if new_token_data:
                return new_token_data.get("access_token")

    # All tokens expired and refresh failed
    return None


def _hash_client_ip(request: Request) -> str:
    """Create a hash of the client IP for state binding."""
    import hashlib
    # Get client IP (consider X-Forwarded-For for proxied requests)
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    # Hash the IP so we don't store raw IPs
    return hashlib.sha256(client_ip.encode()).hexdigest()[:16]


def _cleanup_expired_states():
    """Remove expired OAuth states from in-memory cache.

    Note: Redis states auto-expire via TTL, so this only cleans the
    in-memory fallback cache used when Redis is unavailable.
    """
    # Skip if using Redis (TTL handles expiry automatically)
    if _get_redis():
        return

    now = time.time()
    expired = [
        state for state, data in _state_cache.items()
        if now - data.get("created_at", 0) > STATE_EXPIRY_SECONDS
    ]
    for state in expired:
        del _state_cache[state]


@router.get("/login")
async def login(request: Request, purpose: str = ACCOUNT_PURPOSE_PRIMARY):
    """Initiate Microsoft OAuth login flow.

    Args:
        purpose: Account purpose - 'primary', 'email', or 'storage'
    """
    if purpose not in SCOPES_BY_PURPOSE:
        purpose = ACCOUNT_PURPOSE_PRIMARY

    # Clean up expired states periodically (only for in-memory fallback)
    _cleanup_expired_states()

    state = secrets.token_urlsafe(32)
    state_data = {
        "purpose": purpose,
        "created_at": time.time(),
        "ip_hash": _hash_client_ip(request),
    }

    # Check if user already has a session (adding another account)
    session_id = request.cookies.get("session_id")
    if session_id:
        state_data["existing_session"] = session_id

    # Store state in Redis (with TTL) or in-memory fallback
    _set_state_data(state, state_data)

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
    request: Request,
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

    # Verify state exists (in Redis or memory)
    state_data = _get_state_data(state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    # Verify state hasn't expired (belt-and-suspenders check, Redis TTL should handle this)
    if time.time() - state_data.get("created_at", 0) > STATE_EXPIRY_SECONDS:
        _delete_state_data(state)
        raise HTTPException(status_code=400, detail="OAuth state expired")

    # Verify the callback is from the same client that initiated the flow (CSRF protection)
    current_ip_hash = _hash_client_ip(request)
    if state_data.get("ip_hash") and state_data["ip_hash"] != current_ip_hash:
        logger.warning(
            f"OAuth state IP mismatch: expected {state_data.get('ip_hash')}, got {current_ip_hash}"
        )
        _delete_state_data(state)
        raise HTTPException(status_code=400, detail="Invalid state - client mismatch")

    # Remove state from cache (one-time use)
    _delete_state_data(state)
    purpose = state_data.get("purpose", ACCOUNT_PURPOSE_PRIMARY)
    existing_session = state_data.get("existing_session")

    # Determine session ID first (needed for MSAL cache)
    existing_data = _get_session_data(existing_session) if existing_session else None
    if existing_session and existing_data:
        session_id = existing_session
        session_data = existing_data
    else:
        session_id = secrets.token_urlsafe(32)
        session_data = {}

    # Exchange code for token using MSAL with cache (enables future token refresh)
    app, cache = _get_msal_app_with_cache(session_id, purpose)
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

    # Save MSAL cache for future token refresh
    _save_msal_cache(session_id, purpose, cache)

    # Calculate absolute expiry time if not present
    # MSAL returns expires_in (seconds from now), we need expires_on (Unix timestamp)
    if "expires_in" in result and "expires_on" not in result:
        result["expires_on"] = time.time() + result["expires_in"]

    # Extract user info
    claims = result.get("id_token_claims", {})
    user_info = {
        "name": claims.get("name", "Unknown"),
        "email": claims.get("preferred_username", claims.get("email", "Unknown")),
    }

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
            # Remove just this account and its MSAL cache
            del session_data[purpose]
            _delete_msal_cache(session_id, purpose)

            # If no accounts left, delete entire session
            if not session_data:
                _delete_session_data(session_id)
                response = RedirectResponse(url=settings.frontend_url)
                response.delete_cookie("session_id")
                return response
            _set_session_data(session_id, session_data)
            return RedirectResponse(url=settings.frontend_url)
        else:
            # Remove all accounts and their MSAL caches
            _delete_session_data(session_id)
            for p in [ACCOUNT_PURPOSE_PRIMARY, ACCOUNT_PURPOSE_EMAIL, ACCOUNT_PURPOSE_STORAGE]:
                _delete_msal_cache(session_id, p)

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
