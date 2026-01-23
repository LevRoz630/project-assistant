"""Telegram client service using Telethon for fetching messages."""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

from ..config import get_settings
from telethon import TelegramClient
from telethon.tl.types import (
    Channel,
    Chat,
    Message,
    User,
)

settings = get_settings()

# Global client instance
_client: TelegramClient | None = None
_client_lock = asyncio.Lock()


def _get_session_path() -> str:
    """Get the session file path."""
    session_dir = Path(settings.telegram_session_path)
    session_dir.mkdir(parents=True, exist_ok=True)
    return str(session_dir / "telegram_session")


async def get_client() -> TelegramClient:
    """Get or create the Telegram client."""
    global _client

    async with _client_lock:
        if _client is None or not _client.is_connected():
            if not settings.telegram_api_id or not settings.telegram_api_hash:
                raise ValueError("Telegram API credentials not configured")

            _client = TelegramClient(
                _get_session_path(),
                settings.telegram_api_id,
                settings.telegram_api_hash,
            )
            await _client.connect()

        return _client


async def is_authenticated() -> bool:
    """Check if the client is authenticated."""
    try:
        client = await get_client()
        return await client.is_user_authorized()
    except Exception:
        return False


async def start_auth(phone: str | None = None) -> dict:
    """Start the authentication process."""
    client = await get_client()
    phone = phone or settings.telegram_phone

    if not phone:
        raise ValueError("Phone number not provided")

    if await client.is_user_authorized():
        me = await client.get_me()
        return {
            "status": "already_authenticated",
            "user": {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
            },
        }

    await client.send_code_request(phone)
    return {"status": "code_sent", "phone": phone}


async def complete_auth(phone: str, code: str, password: str | None = None) -> dict:
    """Complete authentication with the code received."""
    client = await get_client()

    try:
        await client.sign_in(phone, code)
    except Exception as e:
        if "Two-step verification" in str(e) or "password" in str(e).lower():
            if not password:
                return {"status": "password_required"}
            await client.sign_in(password=password)
        else:
            raise

    me = await client.get_me()
    return {
        "status": "authenticated",
        "user": {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
        },
    }


async def logout() -> dict:
    """Log out and clear the session."""
    global _client

    if _client:
        await _client.log_out()
        _client = None

    # Remove session file
    session_path = _get_session_path()
    for ext in ["", ".session"]:
        path = f"{session_path}{ext}"
        if os.path.exists(path):
            os.remove(path)

    return {"status": "logged_out"}


def _format_entity(entity) -> dict:
    """Format a Telegram entity (user, chat, channel) for API response."""
    if isinstance(entity, User):
        return {
            "type": "user",
            "id": entity.id,
            "name": f"{entity.first_name or ''} {entity.last_name or ''}".strip(),
            "username": entity.username,
            "phone": entity.phone,
        }
    elif isinstance(entity, Channel):
        return {
            "type": "channel" if entity.broadcast else "group",
            "id": entity.id,
            "name": entity.title,
            "username": entity.username,
        }
    elif isinstance(entity, Chat):
        return {
            "type": "group",
            "id": entity.id,
            "name": entity.title,
        }
    else:
        return {
            "type": "unknown",
            "id": getattr(entity, "id", None),
            "name": str(entity),
        }


def _format_message(message: Message, entity_info: dict) -> dict:
    """Format a Telegram message for API response."""
    return {
        "id": message.id,
        "chat": entity_info,
        "date": message.date.isoformat() if message.date else None,
        "text": message.text or message.message or "",
        "from_id": message.from_id.user_id if message.from_id else None,
        "is_outgoing": message.out,
        "reply_to_msg_id": message.reply_to_msg_id if message.reply_to else None,
        "has_media": message.media is not None,
        "media_type": type(message.media).__name__ if message.media else None,
    }


async def get_dialogs(limit: int = 50, unread_only: bool = False) -> list[dict]:
    """Get recent dialogs (chats)."""
    client = await get_client()

    if not await client.is_user_authorized():
        raise ValueError("Not authenticated")

    dialogs = []
    async for dialog in client.iter_dialogs(limit=limit):
        if unread_only and dialog.unread_count == 0:
            continue

        entity_info = _format_entity(dialog.entity)
        dialogs.append({
            "id": dialog.id,
            "entity": entity_info,
            "name": dialog.name,
            "unread_count": dialog.unread_count,
            "last_message": dialog.message.text if dialog.message else None,
            "last_message_date": dialog.message.date.isoformat() if dialog.message and dialog.message.date else None,
            "is_pinned": dialog.pinned,
            "is_muted": dialog.archived,
        })

    return dialogs


async def get_unread_messages(limit_per_chat: int = 10, max_chats: int = 20) -> list[dict]:
    """Get unread messages from all chats."""
    client = await get_client()

    if not await client.is_user_authorized():
        raise ValueError("Not authenticated")

    all_messages = []
    chat_count = 0

    async for dialog in client.iter_dialogs():
        if dialog.unread_count == 0:
            continue

        if chat_count >= max_chats:
            break

        entity_info = _format_entity(dialog.entity)

        # Get unread messages from this chat
        messages = []
        async for message in client.iter_messages(
            dialog.entity,
            limit=min(dialog.unread_count, limit_per_chat),
        ):
            if message.text or message.message:
                messages.append(_format_message(message, entity_info))

        if messages:
            all_messages.append({
                "chat": entity_info,
                "unread_count": dialog.unread_count,
                "messages": messages,
            })
            chat_count += 1

    return all_messages


async def get_messages(
    chat_id: int,
    limit: int = 50,
    offset_id: int = 0,
    min_date: datetime | None = None,
) -> list[dict]:
    """Get messages from a specific chat."""
    client = await get_client()

    if not await client.is_user_authorized():
        raise ValueError("Not authenticated")

    entity = await client.get_entity(chat_id)
    entity_info = _format_entity(entity)

    messages = []
    async for message in client.iter_messages(
        entity,
        limit=limit,
        offset_id=offset_id,
        offset_date=min_date,
    ):
        messages.append(_format_message(message, entity_info))

    return messages


async def mark_as_read(chat_id: int) -> dict:
    """Mark all messages in a chat as read."""
    client = await get_client()

    if not await client.is_user_authorized():
        raise ValueError("Not authenticated")

    entity = await client.get_entity(chat_id)
    await client.send_read_acknowledge(entity)

    return {"status": "marked_read", "chat_id": chat_id}


async def get_updates_summary(hours: int = 24) -> dict:
    """Get a summary of updates in the last N hours."""
    client = await get_client()

    if not await client.is_user_authorized():
        raise ValueError("Not authenticated")

    since = datetime.now() - timedelta(hours=hours)

    summary = {
        "period_hours": hours,
        "since": since.isoformat(),
        "total_unread": 0,
        "chats_with_unread": 0,
        "channels": [],
        "groups": [],
        "direct_messages": [],
    }

    async for dialog in client.iter_dialogs():
        if dialog.unread_count == 0:
            continue

        summary["total_unread"] += dialog.unread_count
        summary["chats_with_unread"] += 1

        entity_info = _format_entity(dialog.entity)

        # Get preview of unread messages
        preview_messages = []
        async for message in client.iter_messages(dialog.entity, limit=3):
            if message.text:
                preview_messages.append({
                    "text": message.text[:200] + "..." if len(message.text) > 200 else message.text,
                    "date": message.date.isoformat() if message.date else None,
                })

        chat_summary = {
            "id": dialog.id,
            "name": dialog.name,
            "unread_count": dialog.unread_count,
            "preview": preview_messages,
        }

        if entity_info["type"] == "channel":
            summary["channels"].append(chat_summary)
        elif entity_info["type"] == "group":
            summary["groups"].append(chat_summary)
        else:
            summary["direct_messages"].append(chat_summary)

    return summary


async def disconnect():
    """Disconnect the client."""
    global _client

    if _client:
        await _client.disconnect()
        _client = None
