"""Tests for the context cache service."""

import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Mock auth module before importing context_cache
_mock_auth = MagicMock()
_mock_auth._get_redis = MagicMock(return_value=None)
sys.modules["auth"] = _mock_auth

from services.context_cache import (
    CALENDAR_CACHE_TTL,
    CONTEXT_PREFIX,
    EMAIL_CACHE_TTL,
    TASKS_CACHE_TTL,
    _context_cache,
    _get_cache_key,
    _get_ttl,
    get_cached_context,
    invalidate_context,
    set_cached_context,
)


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_get_cache_key_tasks(self):
        """Test cache key format for tasks."""
        key = _get_cache_key("tasks", "session123")
        assert key == f"{CONTEXT_PREFIX}tasks:session123"

    def test_get_cache_key_calendar(self):
        """Test cache key format for calendar."""
        key = _get_cache_key("calendar", "session456")
        assert key == f"{CONTEXT_PREFIX}calendar:session456"

    def test_get_cache_key_email(self):
        """Test cache key format for email."""
        key = _get_cache_key("email", "session789")
        assert key == f"{CONTEXT_PREFIX}email:session789"


class TestTTLConfiguration:
    """Tests for TTL configuration."""

    def test_get_ttl_tasks(self):
        """Test TTL for tasks context."""
        assert _get_ttl("tasks") == TASKS_CACHE_TTL
        assert _get_ttl("tasks") == 120  # 2 minutes

    def test_get_ttl_calendar(self):
        """Test TTL for calendar context."""
        assert _get_ttl("calendar") == CALENDAR_CACHE_TTL
        assert _get_ttl("calendar") == 300  # 5 minutes

    def test_get_ttl_email(self):
        """Test TTL for email context."""
        assert _get_ttl("email") == EMAIL_CACHE_TTL
        assert _get_ttl("email") == 60  # 1 minute

    def test_get_ttl_unknown_defaults_to_300(self):
        """Test TTL for unknown context type defaults to 300."""
        assert _get_ttl("unknown") == 300


class TestCacheWithRedis:
    """Tests for caching with Redis backend."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        return MagicMock()

    def test_get_cached_context_hit(self, mock_redis):
        """Test getting cached context when data exists in Redis."""
        mock_redis.get.return_value = "cached tasks data"

        with patch("services.context_cache._get_redis", return_value=mock_redis):
            result = get_cached_context("tasks", "session123")

        assert result == "cached tasks data"
        mock_redis.get.assert_called_once_with(f"{CONTEXT_PREFIX}tasks:session123")

    def test_get_cached_context_miss(self, mock_redis):
        """Test getting cached context when data doesn't exist in Redis."""
        mock_redis.get.return_value = None

        with patch("services.context_cache._get_redis", return_value=mock_redis):
            result = get_cached_context("tasks", "session123")

        assert result is None

    def test_set_cached_context(self, mock_redis):
        """Test setting cached context in Redis."""
        with patch("services.context_cache._get_redis", return_value=mock_redis):
            set_cached_context("tasks", "session123", "task content")

        mock_redis.setex.assert_called_once_with(
            f"{CONTEXT_PREFIX}tasks:session123",
            TASKS_CACHE_TTL,
            "task content",
        )

    def test_set_cached_context_calendar_ttl(self, mock_redis):
        """Test setting calendar context uses correct TTL."""
        with patch("services.context_cache._get_redis", return_value=mock_redis):
            set_cached_context("calendar", "session123", "calendar content")

        mock_redis.setex.assert_called_once_with(
            f"{CONTEXT_PREFIX}calendar:session123",
            CALENDAR_CACHE_TTL,
            "calendar content",
        )

    def test_invalidate_context(self, mock_redis):
        """Test invalidating cached context in Redis."""
        with patch("services.context_cache._get_redis", return_value=mock_redis):
            invalidate_context("tasks", "session123")

        mock_redis.delete.assert_called_once_with(f"{CONTEXT_PREFIX}tasks:session123")

    def test_get_cached_context_redis_error(self, mock_redis):
        """Test graceful handling of Redis errors on get."""
        mock_redis.get.side_effect = Exception("Redis connection failed")

        with patch("services.context_cache._get_redis", return_value=mock_redis):
            result = get_cached_context("tasks", "session123")

        assert result is None

    def test_set_cached_context_redis_error(self, mock_redis):
        """Test graceful handling of Redis errors on set."""
        mock_redis.setex.side_effect = Exception("Redis connection failed")

        with patch("services.context_cache._get_redis", return_value=mock_redis):
            # Should not raise
            set_cached_context("tasks", "session123", "content")

    def test_invalidate_context_redis_error(self, mock_redis):
        """Test graceful handling of Redis errors on invalidate."""
        mock_redis.delete.side_effect = Exception("Redis connection failed")

        with patch("services.context_cache._get_redis", return_value=mock_redis):
            # Should not raise
            invalidate_context("tasks", "session123")


class TestCacheWithMemoryFallback:
    """Tests for caching with in-memory fallback (no Redis)."""

    @pytest.fixture(autouse=True)
    def clear_memory_cache(self):
        """Clear the in-memory cache before each test."""
        _context_cache.clear()
        yield
        _context_cache.clear()

    def test_set_and_get_cached_context(self):
        """Test setting and getting cached context in memory."""
        with patch("services.context_cache._get_redis", return_value=None):
            set_cached_context("tasks", "session123", "task content")
            result = get_cached_context("tasks", "session123")

        assert result == "task content"

    def test_get_cached_context_not_exists(self):
        """Test getting non-existent cached context from memory."""
        with patch("services.context_cache._get_redis", return_value=None):
            result = get_cached_context("tasks", "session123")

        assert result is None

    def test_cached_context_expires(self):
        """Test that cached context expires after TTL."""
        with patch("services.context_cache._get_redis", return_value=None):
            # Set cache
            set_cached_context("email", "session123", "email content")

            # Manually expire the cache entry
            key = _get_cache_key("email", "session123")
            content, _ = _context_cache[key]
            expired_time = datetime.now() - timedelta(seconds=EMAIL_CACHE_TTL + 10)
            _context_cache[key] = (content, expired_time)

            # Should return None and clean up
            result = get_cached_context("email", "session123")

        assert result is None
        assert key not in _context_cache

    def test_invalidate_context_memory(self):
        """Test invalidating cached context from memory."""
        with patch("services.context_cache._get_redis", return_value=None):
            set_cached_context("tasks", "session123", "task content")
            invalidate_context("tasks", "session123")
            result = get_cached_context("tasks", "session123")

        assert result is None

    def test_invalidate_nonexistent_context(self):
        """Test invalidating non-existent context doesn't raise."""
        with patch("services.context_cache._get_redis", return_value=None):
            # Should not raise
            invalidate_context("tasks", "nonexistent")

    def test_different_sessions_independent(self):
        """Test that different sessions have independent caches."""
        with patch("services.context_cache._get_redis", return_value=None):
            set_cached_context("tasks", "session1", "session1 tasks")
            set_cached_context("tasks", "session2", "session2 tasks")

            result1 = get_cached_context("tasks", "session1")
            result2 = get_cached_context("tasks", "session2")

        assert result1 == "session1 tasks"
        assert result2 == "session2 tasks"

    def test_different_context_types_independent(self):
        """Test that different context types have independent caches."""
        with patch("services.context_cache._get_redis", return_value=None):
            set_cached_context("tasks", "session123", "tasks content")
            set_cached_context("calendar", "session123", "calendar content")
            set_cached_context("email", "session123", "email content")

            tasks = get_cached_context("tasks", "session123")
            calendar = get_cached_context("calendar", "session123")
            email = get_cached_context("email", "session123")

        assert tasks == "tasks content"
        assert calendar == "calendar content"
        assert email == "email content"


class TestCacheIntegration:
    """Integration tests for cache behavior."""

    @pytest.fixture(autouse=True)
    def clear_memory_cache(self):
        """Clear the in-memory cache before each test."""
        _context_cache.clear()
        yield
        _context_cache.clear()

    def test_cache_workflow_with_invalidation(self):
        """Test typical cache workflow: set, get, invalidate, get."""
        with patch("services.context_cache._get_redis", return_value=None):
            # Initial state - no cache
            assert get_cached_context("tasks", "session123") is None

            # Set cache
            set_cached_context("tasks", "session123", "initial tasks")
            assert get_cached_context("tasks", "session123") == "initial tasks"

            # Invalidate
            invalidate_context("tasks", "session123")
            assert get_cached_context("tasks", "session123") is None

            # Set new value
            set_cached_context("tasks", "session123", "updated tasks")
            assert get_cached_context("tasks", "session123") == "updated tasks"

    def test_invalidate_only_affects_specific_context(self):
        """Test that invalidation only affects the specific context type."""
        with patch("services.context_cache._get_redis", return_value=None):
            set_cached_context("tasks", "session123", "tasks content")
            set_cached_context("calendar", "session123", "calendar content")

            # Invalidate only tasks
            invalidate_context("tasks", "session123")

            # Tasks should be gone, calendar should remain
            assert get_cached_context("tasks", "session123") is None
            assert get_cached_context("calendar", "session123") == "calendar content"
