"""Email endpoints for reading and managing emails."""

from ..auth import get_access_token
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..services.graph import GraphClient

router = APIRouter(prefix="/email", tags=["email"])


class EmailSummary(BaseModel):
    """Summary of an email message."""

    id: str
    subject: str
    from_name: str
    from_email: str
    received: str
    is_read: bool
    preview: str


@router.get("/inbox")
async def get_inbox(
    request: Request,
    top: int = 20,
    skip: int = 0,
):
    """Get inbox messages."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    client = GraphClient(token)

    try:
        result = await client.list_messages("inbox", top=top, skip=skip)
        messages = result.get("value", [])

        summaries = []
        for msg in messages:
            from_info = msg.get("from", {}).get("emailAddress", {})
            summaries.append(
                {
                    "id": msg.get("id"),
                    "subject": msg.get("subject", "(No subject)"),
                    "from_name": from_info.get("name", "Unknown"),
                    "from_email": from_info.get("address", ""),
                    "received": msg.get("receivedDateTime", ""),
                    "is_read": msg.get("isRead", False),
                    "preview": msg.get("bodyPreview", "")[:200],
                }
            )

        return {
            "messages": summaries,
            "count": len(summaries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {e}") from e


@router.get("/folder/{folder_id}")
async def get_folder_messages(
    request: Request,
    folder_id: str,
    top: int = 20,
    skip: int = 0,
):
    """Get messages from a specific folder."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    client = GraphClient(token)

    try:
        result = await client.list_messages(folder_id, top=top, skip=skip)
        messages = result.get("value", [])

        summaries = []
        for msg in messages:
            from_info = msg.get("from", {}).get("emailAddress", {})
            summaries.append(
                {
                    "id": msg.get("id"),
                    "subject": msg.get("subject", "(No subject)"),
                    "from_name": from_info.get("name", "Unknown"),
                    "from_email": from_info.get("address", ""),
                    "received": msg.get("receivedDateTime", ""),
                    "is_read": msg.get("isRead", False),
                    "preview": msg.get("bodyPreview", "")[:200],
                }
            )

        return {
            "folder_id": folder_id,
            "messages": summaries,
            "count": len(summaries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch folder emails: {e}") from e


@router.get("/message/{message_id}")
async def get_message(request: Request, message_id: str):
    """Get a specific email message."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    client = GraphClient(token)

    try:
        msg = await client.get_message(message_id)

        from_info = msg.get("from", {}).get("emailAddress", {})
        to_recipients = [
            r.get("emailAddress", {}).get("address", "") for r in msg.get("toRecipients", [])
        ]

        return {
            "id": msg.get("id"),
            "subject": msg.get("subject", "(No subject)"),
            "from_name": from_info.get("name", "Unknown"),
            "from_email": from_info.get("address", ""),
            "to": to_recipients,
            "received": msg.get("receivedDateTime", ""),
            "is_read": msg.get("isRead", False),
            "body": msg.get("body", {}).get("content", ""),
            "body_type": msg.get("body", {}).get("contentType", "text"),
            "has_attachments": msg.get("hasAttachments", False),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch email: {e}") from e


@router.get("/search")
async def search_emails(
    request: Request,
    query: str,
    top: int = 20,
):
    """Search email messages."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    client = GraphClient(token)

    try:
        result = await client.search_messages(query, top=top)
        messages = result.get("value", [])

        summaries = []
        for msg in messages:
            from_info = msg.get("from", {}).get("emailAddress", {})
            summaries.append(
                {
                    "id": msg.get("id"),
                    "subject": msg.get("subject", "(No subject)"),
                    "from_name": from_info.get("name", "Unknown"),
                    "from_email": from_info.get("address", ""),
                    "received": msg.get("receivedDateTime", ""),
                    "is_read": msg.get("isRead", False),
                    "preview": msg.get("bodyPreview", "")[:200],
                }
            )

        return {
            "query": query,
            "messages": summaries,
            "count": len(summaries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search emails: {e}") from e


@router.get("/folders")
async def get_folders(request: Request):
    """Get email folders (inbox, sent, drafts, etc.)."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    client = GraphClient(token)

    try:
        result = await client._request("GET", "/me/mailFolders")
        folders = result.get("value", [])

        return {
            "folders": [
                {
                    "id": f.get("id"),
                    "name": f.get("displayName"),
                    "unread_count": f.get("unreadItemCount", 0),
                    "total_count": f.get("totalItemCount", 0),
                }
                for f in folders
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch folders: {e}") from e
