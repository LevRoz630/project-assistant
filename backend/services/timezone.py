"""Timezone resolution from request headers with config fallback."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Request

from backend.config import get_settings


def resolve_timezone(request: Request) -> str:
    """Extract timezone from X-Timezone header, falling back to config default.

    Validates that the header value is a real IANA timezone identifier.
    """
    header_tz = request.headers.get("X-Timezone")
    if header_tz:
        try:
            ZoneInfo(header_tz)
            return header_tz
        except (ZoneInfoNotFoundError, KeyError):
            pass
    return get_settings().timezone


def now_in_tz(request: Request) -> datetime:
    """Return the current datetime in the timezone resolved from the request."""
    tz = ZoneInfo(resolve_timezone(request))
    return datetime.now(tz)
