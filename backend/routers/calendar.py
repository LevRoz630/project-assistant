"""Calendar endpoints - Outlook integration."""

import logging
from datetime import datetime, timedelta

from ..auth import get_access_token_for_service
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from ..services.graph import GraphClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


def get_graph_client(request: Request) -> GraphClient:
    """Dependency to get authenticated Graph client for calendar."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token_for_service(session_id, "calendar")
    if not token:
        raise HTTPException(
            status_code=401, detail="Session expired or no calendar account configured"
        )

    return GraphClient(token)


class EventCreate(BaseModel):
    """Request body for creating a calendar event."""

    subject: str
    start: str  # ISO format: 2026-01-21T10:00:00
    end: str  # ISO format: 2026-01-21T11:00:00
    body: str | None = None
    location: str | None = None
    attendees: list[str] | None = None  # Email addresses


@router.get("/list")
async def list_calendars(client: GraphClient = Depends(get_graph_client)):
    """List all calendars."""
    try:
        result = await client.list_calendars()
        calendars = [
            {
                "id": cal["id"],
                "name": cal["name"],
                "color": cal.get("color"),
                "is_default": cal.get("isDefaultCalendar", False),
                "can_edit": cal.get("canEdit", True),
            }
            for cal in result.get("value", [])
        ]
        return {"calendars": calendars}
    except Exception as e:
        logger.exception("Failed to list calendars")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/today")
async def get_today_events(client: GraphClient = Depends(get_graph_client)):
    """Get today's calendar events."""
    try:
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = await client.get_calendar_view(
            start_datetime=start.isoformat(),
            end_datetime=end.isoformat(),
        )

        events = _format_events(result.get("value", []))
        return {"date": start.strftime("%Y-%m-%d"), "events": events}
    except Exception as e:
        logger.exception("Failed to get today's events")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/week")
async def get_week_events(client: GraphClient = Depends(get_graph_client)):
    """Get this week's calendar events."""
    try:
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)

        result = await client.get_calendar_view(
            start_datetime=start.isoformat(),
            end_datetime=end.isoformat(),
        )

        events = _format_events(result.get("value", []))

        # Group by date
        grouped = {}
        for event in events:
            date = event["start_date"]
            if date not in grouped:
                grouped[date] = []
            grouped[date].append(event)

        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "events_by_date": grouped,
            "total_events": len(events),
        }
    except Exception as e:
        logger.exception("Failed to get week's events")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/range")
async def get_events_range(
    start_date: str,  # YYYY-MM-DD
    end_date: str,  # YYYY-MM-DD
    client: GraphClient = Depends(get_graph_client),
):
    """Get calendar events in a date range."""
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) + timedelta(days=1)

        result = await client.get_calendar_view(
            start_datetime=start.isoformat(),
            end_datetime=end.isoformat(),
        )

        events = _format_events(result.get("value", []))
        return {
            "start": start_date,
            "end": end_date,
            "events": events,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/create")
async def create_event(
    event: EventCreate,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a new calendar event."""
    try:
        result = await client.create_event(
            subject=event.subject,
            start_datetime=event.start,
            end_datetime=event.end,
            body=event.body,
            location=event.location,
            attendees=event.attendees,
        )

        return {
            "success": True,
            "event": {
                "id": result["id"],
                "subject": result["subject"],
                "start": result["start"]["dateTime"],
                "end": result["end"]["dateTime"],
                "web_link": result.get("webLink"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/delete/{event_id}")
async def delete_event(
    event_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Delete a calendar event."""
    try:
        await client.delete_event(event_id)
        return {"success": True, "deleted": event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _format_events(events: list) -> list:
    """Format event data for response."""
    formatted = []
    for event in events:
        start_dt = event["start"]["dateTime"]
        end_dt = event["end"]["dateTime"]

        # Parse dates
        try:
            start_parsed = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            end_parsed = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
        except Exception:
            start_parsed = None
            end_parsed = None

        formatted.append(
            {
                "id": event["id"],
                "subject": event["subject"],
                "start": start_dt,
                "end": end_dt,
                "start_date": start_parsed.strftime("%Y-%m-%d") if start_parsed else None,
                "start_time": start_parsed.strftime("%H:%M") if start_parsed else None,
                "end_time": end_parsed.strftime("%H:%M") if end_parsed else None,
                "is_all_day": event.get("isAllDay", False),
                "location": event.get("location", {}).get("displayName"),
                "body_preview": event.get("bodyPreview", ""),
                "organizer": event.get("organizer", {}).get("emailAddress", {}).get("name"),
                "web_link": event.get("webLink"),
                "response_status": event.get("responseStatus", {}).get("response"),
            }
        )

    return formatted
