"""Context caching service using Redis.

Caches context data (tasks, calendar, email) to avoid repeated Graph API
calls during chat sessions. Uses TTL-based expiration with in-memory fallback
when Redis is unavailable.
"""

import logging
from datetime import datetime, timedelta

try:
    from ..auth import _get_redis
except ImportError:
    from auth import _get_redis

logger = logging.getLogger(__name__)

# Cache TTLs in seconds (short for freshness)
TASKS_CACHE_TTL = 120      # 2 minutes
CALENDAR_CACHE_TTL = 300   # 5 minutes
EMAIL_CACHE_TTL = 60       # 1 minute

CONTEXT_PREFIX = "context:"

# In-memory fallback when Redis unavailable
_context_cache: dict[str, tuple[str, datetime]] = {}


def _get_cache_key(context_type: str, session_id: str) -> str:
    """Build cache key for context data."""
    return f"{CONTEXT_PREFIX}{context_type}:{session_id}"


def _get_ttl(context_type: str) -> int:
    """Get TTL in seconds for a context type."""
    ttl_map = {
        "tasks": TASKS_CACHE_TTL,
        "calendar": CALENDAR_CACHE_TTL,
        "email": EMAIL_CACHE_TTL,
    }
    return ttl_map.get(context_type, 300)


def get_cached_context(context_type: str, session_id: str) -> str | None:
    """Get cached context, returns None if not cached or expired.

    Args:
        context_type: One of 'tasks', 'calendar', 'email'
        session_id: User session ID

    Returns:
        Cached context string or None if not available
    """
    key = _get_cache_key(context_type, session_id)
    redis = _get_redis()

    if redis:
        try:
            data = redis.get(key)
            if data:
                logger.debug(f"Cache hit for {context_type}")
                return data
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")
        return None

    # In-memory fallback
    if key in _context_cache:
        content, cached_at = _context_cache[key]
        ttl = _get_ttl(context_type)
        if datetime.now() - cached_at < timedelta(seconds=ttl):
            logger.debug(f"Memory cache hit for {context_type}")
            return content
        # Expired - clean up
        del _context_cache[key]

    return None


def set_cached_context(context_type: str, session_id: str, content: str) -> None:
    """Cache context with appropriate TTL.

    Args:
        context_type: One of 'tasks', 'calendar', 'email'
        session_id: User session ID
        content: Context content to cache
    """
    key = _get_cache_key(context_type, session_id)
    ttl = _get_ttl(context_type)
    redis = _get_redis()

    if redis:
        try:
            redis.setex(key, ttl, content)
            logger.debug(f"Cached {context_type} for {ttl}s")
        except Exception as e:
            logger.warning(f"Redis setex failed for {key}: {e}")
    else:
        # In-memory fallback
        _context_cache[key] = (content, datetime.now())
        logger.debug(f"Memory cached {context_type}")


def invalidate_context(context_type: str, session_id: str) -> None:
    """Invalidate cached context (call after user makes changes).

    Args:
        context_type: One of 'tasks', 'calendar', 'email'
        session_id: User session ID
    """
    key = _get_cache_key(context_type, session_id)
    redis = _get_redis()

    if redis:
        try:
            redis.delete(key)
            logger.debug(f"Invalidated cache for {context_type}")
        except Exception as e:
            logger.warning(f"Redis delete failed for {key}: {e}")
    elif key in _context_cache:
        del _context_cache[key]
        logger.debug(f"Invalidated memory cache for {context_type}")
