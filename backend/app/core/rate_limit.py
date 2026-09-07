"""Redis-Backed Production Rate Limiter Module."""

import time
import logging
from typing import Optional
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None


async def get_redis_client() -> Optional[Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            from app.core.config import settings
            _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Could not initialize Redis client for rate limiting: {e}")
            return None
    return _redis_client


async def check_rate_limit(
    key: str,
    max_requests: int = 60,
    window_seconds: int = 60
) -> bool:
    """Sliding-window rate limiter checking if key has exceeded max_requests in window_seconds."""
    redis = await get_redis_client()
    if not redis:
        return True  # Gracefully allow if Redis is unavailable

    now = time.time()
    cutoff = now - window_seconds
    redis_key = f"rate_limit:{key}"

    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(redis_key, 0, cutoff)
            pipe.zadd(redis_key, {str(now): now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window_seconds)
            results = await pipe.execute()

        request_count = results[2]
        return request_count <= max_requests
    except Exception as e:
        logger.warning(f"Rate limiting check failed: {e}. Degrading gracefully.")
        return True
