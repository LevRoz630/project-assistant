"""Telegram integration endpoints for fetching messages."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..services import telegram

router = APIRouter(prefix="/telegram", tags=["telegram"])


def _require_auth(request: Request):
    """Check if user is authenticated to the app."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated to app")


class AuthStartRequest(BaseModel):
    """Request to start Telegram authentication."""

    phone: str | None = None


class AuthCompleteRequest(BaseModel):
    """Request to complete Telegram authentication."""

    phone: str
    code: str
    password: str | None = None


# ==================== Authentication ====================


@router.get("/status")
async def get_status(request: Request):
    """Check Telegram authentication status."""
    _require_auth(request)

    try:
        authenticated = await telegram.is_authenticated()
        if authenticated:
            client = await telegram.get_client()
            me = await client.get_me()
            return {
                "authenticated": True,
                "user": {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "phone": me.phone,
                },
            }
        return {"authenticated": False}
    except ValueError as e:
        return {"authenticated": False, "error": str(e), "needs_config": True}
    except Exception as e:
        return {"authenticated": False, "error": str(e)}


@router.post("/auth/start")
async def start_auth(request: Request, auth_request: AuthStartRequest):
    """Start Telegram authentication - sends code to phone."""
    _require_auth(request)

    try:
        result = await telegram.start_auth(auth_request.phone)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/auth/complete")
async def complete_auth(request: Request, auth_request: AuthCompleteRequest):
    """Complete Telegram authentication with the received code."""
    _require_auth(request)

    try:
        result = await telegram.complete_auth(
            auth_request.phone,
            auth_request.code,
            auth_request.password,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/auth/logout")
async def logout(request: Request):
    """Log out from Telegram."""
    _require_auth(request)

    try:
        result = await telegram.logout()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Dialogs / Chats ====================


@router.get("/dialogs")
async def get_dialogs(
    request: Request,
    limit: int = 50,
    unread_only: bool = False,
):
    """Get list of chats/dialogs."""
    _require_auth(request)

    try:
        dialogs = await telegram.get_dialogs(limit=limit, unread_only=unread_only)
        return {"dialogs": dialogs, "count": len(dialogs)}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Messages ====================


@router.get("/unread")
async def get_unread(
    request: Request,
    limit_per_chat: int = 10,
    max_chats: int = 20,
):
    """Get unread messages from all chats."""
    _require_auth(request)

    try:
        messages = await telegram.get_unread_messages(
            limit_per_chat=limit_per_chat,
            max_chats=max_chats,
        )
        total_unread = sum(chat["unread_count"] for chat in messages)
        return {
            "chats_with_unread": len(messages),
            "total_unread": total_unread,
            "messages": messages,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/messages/{chat_id}")
async def get_messages(
    request: Request,
    chat_id: int,
    limit: int = 50,
    offset_id: int = 0,
    hours_back: int | None = None,
):
    """Get messages from a specific chat."""
    _require_auth(request)

    try:
        min_date = None
        if hours_back:
            min_date = datetime.now() - timedelta(hours=hours_back)

        messages = await telegram.get_messages(
            chat_id=chat_id,
            limit=limit,
            offset_id=offset_id,
            min_date=min_date,
        )
        return {"chat_id": chat_id, "messages": messages, "count": len(messages)}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/messages/{chat_id}/read")
async def mark_as_read(request: Request, chat_id: int):
    """Mark all messages in a chat as read."""
    _require_auth(request)

    try:
        result = await telegram.mark_as_read(chat_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Summary ====================


@router.get("/summary")
async def get_summary(request: Request, hours: int = 24):
    """Get a summary of Telegram updates in the last N hours."""
    _require_auth(request)

    try:
        summary = await telegram.get_updates_summary(hours=hours)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
