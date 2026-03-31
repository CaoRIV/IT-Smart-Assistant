"""Rate limiter for Gemini API calls.

Prevents hitting rate limits by tracking and throttling requests.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import ClassVar

from app.clients.redis import RedisClient
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Requests per minute (Gemini 1.5 Flash free tier: 15 req/min)
    requests_per_minute: int = 15
    # Requests per day (Gemini 1.5 Flash free tier: 1500 req/day)
    requests_per_day: int = 1500
    # Burst allowance (allow small bursts)
    burst_size: int = 5


class GeminiRateLimiter:
    """Rate limiter for Gemini API with Redis backend.
    
    Implements token bucket algorithm with per-user tracking.
    """

    _instance: ClassVar[GeminiRateLimiter | None] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> GeminiRateLimiter:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        redis_client: RedisClient | None = None,
        config: RateLimitConfig | None = None,
    ):
        if hasattr(self, "_initialized"):
            return

        self.redis = redis_client or RedisClient()
        self.config = config or RateLimitConfig()
        self._initialized = True
        self._local_cache: dict[str, dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to Redis."""
        await self.redis.connect()

    def _key_minute(self, user_id: str) -> str:
        """Redis key for per-minute counter."""
        minute = int(time.time() // 60)
        return f"ratelimit:{user_id}:minute:{minute}"

    def _key_day(self, user_id: str) -> str:
        """Redis key for per-day counter."""
        day = int(time.time() // 86400)
        return f"ratelimit:{user_id}:day:{day}"

    async def check_rate_limit(
        self,
        user_id: str,
        requested_tokens: int = 1,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is within rate limits.

        Args:
            user_id: User identifier for per-user tracking
            requested_tokens: Number of tokens (requests) to consume

        Returns:
            Tuple of (allowed: bool, info: dict)
            info contains: remaining_minute, remaining_day, retry_after_seconds
        """
        minute_key = self._key_minute(user_id)
        day_key = self._key_day(user_id)

        # Get current counts
        minute_count = await self._get_count(minute_key, 60)
        day_count = await self._get_count(day_key, 86400)

        # Calculate remaining
        remaining_minute = max(0, self.config.requests_per_minute - minute_count)
        remaining_day = max(0, self.config.requests_per_day - day_count)

        info = {
            "remaining_minute": remaining_minute,
            "remaining_day": remaining_day,
            "minute_count": minute_count,
            "day_count": day_count,
            "retry_after_seconds": None,
        }

        # Check limits
        if day_count + requested_tokens > self.config.requests_per_day:
            # Daily limit exceeded
            info["retry_after_seconds"] = self._seconds_until_next_day()
            logger.warning(f"Daily rate limit exceeded for user {user_id}")
            return False, info

        if minute_count + requested_tokens > self.config.requests_per_minute:
            # Minute limit exceeded
            info["retry_after_seconds"] = self._seconds_until_next_minute()
            logger.warning(f"Minute rate limit exceeded for user {user_id}")
            return False, info

        return True, info

    async def _get_count(self, key: str, ttl: int) -> int:
        """Get counter value from Redis or cache."""
        # Try local cache first
        async with self._cache_lock:
            if key in self._local_cache:
                cached = self._local_cache[key]
                if cached["expires"] > time.time():
                    return cached["count"]
                else:
                    del self._local_cache[key]

        # Try Redis
        try:
            value = await self.redis.get(key)
            count = int(value) if value else 0

            # Update local cache
            async with self._cache_lock:
                self._local_cache[key] = {
                    "count": count,
                    "expires": time.time() + 1,  # Cache for 1 second
                }
            return count
        except Exception as e:
            logger.error(f"Failed to get rate limit count: {e}")
            return 0

    async def record_request(
        self,
        user_id: str,
        tokens: int = 1,
    ) -> dict[str, Any]:
        """Record a request and update counters.

        Args:
            user_id: User identifier
            tokens: Number of tokens to consume

        Returns:
            Updated rate limit info
        """
        minute_key = self._key_minute(user_id)
        day_key = self._key_day(user_id)

        try:
            # Increment counters (with TTL if new)
            minute_count = await self._increment(minute_key, 60)
            day_count = await self._increment(day_key, 86400)

            remaining_minute = max(0, self.config.requests_per_minute - minute_count)
            remaining_day = max(0, self.config.requests_per_day - day_count)

            return {
                "remaining_minute": remaining_minute,
                "remaining_day": remaining_day,
                "minute_count": minute_count,
                "day_count": day_count,
            }
        except Exception as e:
            logger.error(f"Failed to record request: {e}")
            return {
                "remaining_minute": 0,
                "remaining_day": 0,
                "error": str(e),
            }

    async def _increment(self, key: str, ttl: int) -> int:
        """Increment counter in Redis."""
        try:
            # Use raw Redis client for atomic operations
            redis = self.redis.raw

            # Try to increment existing key
            new_val = await redis.incr(key)

            if new_val == 1:
                # Key was just created, set TTL
                await redis.expire(key, ttl)

            # Update local cache
            async with self._cache_lock:
                self._local_cache[key] = {
                    "count": int(new_val),
                    "expires": time.time() + 1,
                }

            return int(new_val)
        except Exception as e:
            logger.error(f"Redis increment failed: {e}")
            return 0

    def _seconds_until_next_minute(self) -> int:
        """Calculate seconds until next minute starts."""
        now = time.time()
        return 60 - int(now % 60)

    def _seconds_until_next_day(self) -> int:
        """Calculate seconds until next day starts (UTC)."""
        now = time.time()
        return 86400 - int(now % 86400)

    async def acquire(
        self,
        user_id: str,
        tokens: int = 1,
        timeout: float | None = None,
    ) -> bool:
        """Acquire permission to make a request, optionally waiting.

        Args:
            user_id: User identifier
            tokens: Number of tokens needed
            timeout: Maximum time to wait (seconds), None for no wait

        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()

        while True:
            allowed, info = await self.check_rate_limit(user_id, tokens)

            if allowed:
                await self.record_request(user_id, tokens)
                return True

            if timeout is None:
                return False

            # Calculate wait time
            retry_after = info.get("retry_after_seconds", 1)
            elapsed = time.time() - start_time

            if elapsed + retry_after > timeout:
                return False

            logger.info(f"Rate limit hit, waiting {retry_after}s...")
            await asyncio.sleep(min(retry_after, 5))  # Max 5s per wait

    async def get_status(self, user_id: str) -> dict[str, Any]:
        """Get current rate limit status for user."""
        allowed, info = await self.check_rate_limit(user_id, 0)
        return {
            "user_id": user_id,
            "allowed": allowed,
            "limits": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_day": self.config.requests_per_day,
            },
            "current": {
                "minute_count": info["minute_count"],
                "day_count": info["day_count"],
            },
            "remaining": {
                "minute": info["remaining_minute"],
                "day": info["remaining_day"],
            },
        }

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()


# Global instance (lazy initialization)
_rate_limiter: GeminiRateLimiter | None = None


async def get_rate_limiter() -> GeminiRateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = GeminiRateLimiter()
        await _rate_limiter.connect()
    return _rate_limiter


async def check_rate_limit(
    user_id: str,
    tokens: int = 1,
) -> tuple[bool, dict[str, Any]]:
    """Convenience function to check rate limit."""
    limiter = await get_rate_limiter()
    return await limiter.check_rate_limit(user_id, tokens)
