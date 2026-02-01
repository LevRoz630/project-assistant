"""Redis-backed chat history storage."""

import json
import logging

from ..auth import _get_redis

logger = logging.getLogger(__name__)

CHAT_HISTORY_PREFIX = "chat_history:"
CHAT_HISTORY_TTL = 60 * 60 * 24 * 30  # 30 days
MAX_CONVERSATIONS = 10


def get_chat_history(session_id: str) -> list[dict]:
    """Get chat history from Redis."""
    redis = _get_redis()
    if redis:
        try:
            data = redis.get(f"{CHAT_HISTORY_PREFIX}{session_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to get chat history from Redis: {e}")
    return []


def save_chat_history(session_id: str, conversations: list[dict]) -> bool:
    """Save chat history to Redis, keeping only last MAX_CONVERSATIONS."""
    redis = _get_redis()
    if not redis:
        logger.debug("Redis not available, chat history not saved")
        return False

    # Sort by updatedAt desc, keep only MAX_CONVERSATIONS
    sorted_convs = sorted(
        conversations,
        key=lambda c: c.get("updatedAt", ""),
        reverse=True
    )[:MAX_CONVERSATIONS]

    try:
        redis.setex(
            f"{CHAT_HISTORY_PREFIX}{session_id}",
            CHAT_HISTORY_TTL,
            json.dumps(sorted_convs)
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to save chat history to Redis: {e}")
        return False


def delete_conversation(session_id: str, conversation_id: str) -> bool:
    """Delete a specific conversation from history."""
    history = get_chat_history(session_id)
    original_count = len(history)
    history = [c for c in history if c.get("id") != conversation_id]

    if len(history) == original_count:
        # Conversation not found
        return False

    return save_chat_history(session_id, history)
