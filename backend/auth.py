"""Microsoft OAuth authentication using MSAL with multi-account support."""

import secrets

import msal
from config import get_settings
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

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

# In-memory token cache (use Redis/database in production)
_token_cache: dict[str, dict[str, dict]] = {}  # {session_id: {purpose: {token_data, user_info}}}
_state_cache: dict[str, dict] = {}  # {state: {purpose: str}}


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
    if session_id not in _token_cache:
        return None

    session_data = _token_cache[session_id]

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
    if session_id not in _token_cache:
        return None

    session_data = _token_cache[session_id]

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
    if existing_session and existing_session in _token_cache:
        session_id = existing_session
    else:
        session_id = secrets.token_urlsafe(32)
        _token_cache[session_id] = {}

    # Store token under the purpose key
    _token_cache[session_id][purpose] = {
        "token_data": result,
        "user_info": user_info,
    }

    # Redirect to frontend with session cookie
    response = RedirectResponse(url=settings.frontend_url)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
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

    if session_id and session_id in _token_cache:
        if purpose and purpose in _token_cache[session_id]:
            # Remove just this account
            del _token_cache[session_id][purpose]
            # If no accounts left, delete session
            if not _token_cache[session_id]:
                del _token_cache[session_id]
                response = RedirectResponse(url=settings.frontend_url)
                response.delete_cookie("session_id")
                return response
            return RedirectResponse(url=settings.frontend_url)
        else:
            # Remove all accounts
            del _token_cache[session_id]

    response = RedirectResponse(url=settings.frontend_url)
    response.delete_cookie("session_id")

    return response


@router.get("/me")
async def get_current_user(request: Request):
    """Get current user info (primary account)."""
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if session_id not in _token_cache or not _token_cache[session_id]:
        raise HTTPException(status_code=401, detail="Session expired")

    session_data = _token_cache[session_id]

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

    if session_id not in _token_cache:
        raise HTTPException(status_code=401, detail="Session expired")

    session_data = _token_cache[session_id]
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
