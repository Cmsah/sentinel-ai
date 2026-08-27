"""Async Redis client with connection pooling.

Used for:
- Caching AI analysis results
- Rate limiting API endpoints
- Distributed locks for concurrent operations
- Pub/Sub for real-time notifications
"""

from __future__ import annotations

from typing import Any

import structlog
from redis.asyncio import ConnectionPool, Redis

from services.shared.config import get_settings

logger = structlog.get_logger(__name__)

_pool: ConnectionPool | None = None
_client: Redis | None = None


async def get_redis() -> Redis:
    """Return the shared async Redis client."""
    global _pool, _client
    if _client is None:
        settings = get_settings()
        _pool = ConnectionPool.from_url(
            settings.redis.url,
            max_connections=settings.redis.max_connections,
            socket_timeout=settings.redis.socket_timeout,
            decode_responses=settings.redis.decode_responses,
        )
        _client = Redis(connection_pool=_pool)
        logger.info("redis_connected", url=settings.redis.url)
    return _client


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _pool, _client
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
    logger.info("redis_disconnected")


async def cache_get(key: str) -> str | None:
    """Get a cached value by key."""
    client = await get_redis()
    return await client.get(key)


async def cache_set(key: str, value: str, ttl_seconds: int = 300) -> None:
    """Set a cached value with TTL."""
    client = await get_redis()
    await client.set(key, value, ex=ttl_seconds)


async def cache_delete(key: str) -> None:
    """Delete a cached value."""
    client = await get_redis()
    await client.delete(key)


async def acquire_lock(lock_name: str, ttl_seconds: int = 30) -> str | None:
    """Acquire a distributed lock. Returns lock token or None."""
    import uuid

    client = await get_redis()
    token = str(uuid.uuid4())
    acquired = await client.set(f"lock:{lock_name}", token, nx=True, ex=ttl_seconds)
    return token if acquired else None


async def release_lock(lock_name: str, token: str) -> bool:
    """Release a distributed lock if we still own it."""
    client = await get_redis()
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    result = await client.eval(script, 1, f"lock:{lock_name}", token)
    return result == 1
