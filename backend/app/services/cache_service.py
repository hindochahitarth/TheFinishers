"""
Service: Redis Cache Layer
Shared helpers for caching API responses, sensor data, and agent state.
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create Redis connection pool."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


async def cache_set(key: str, value: Any, ttl: int = settings.cache_ttl_seconds) -> bool:
    """Serialize and store value in Redis with TTL."""
    try:
        redis = await get_redis()
        serialized = json.dumps(value, default=str)
        await redis.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f"Redis SET failed key={key}: {e}")
        return False


async def cache_get(key: str) -> Optional[Any]:
    """Retrieve and deserialize value from Redis."""
    try:
        redis = await get_redis()
        raw = await redis.get(key)
        if raw:
            return json.loads(raw)
        return None
    except Exception as e:
        logger.warning(f"Redis GET failed key={key}: {e}")
        return None


async def cache_delete(key: str) -> bool:
    try:
        redis = await get_redis()
        await redis.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis DEL failed key={key}: {e}")
        return False


async def publish_event(channel: str, event: dict) -> bool:
    """Publish a real-time event to Redis pub/sub channel."""
    try:
        redis = await get_redis()
        await redis.publish(channel, json.dumps(event, default=str))
        return True
    except Exception as e:
        logger.warning(f"Redis PUBLISH failed channel={channel}: {e}")
        return False


# Cache key helpers
def key_current_conditions(location_id: int) -> str:
    return f"greenpulse:current:{location_id}"

def key_forecast(location_id: int, hours: int) -> str:
    return f"greenpulse:forecast:{location_id}:{hours}h"

def key_compliance(location_id: int) -> str:
    return f"greenpulse:compliance:{location_id}"

def key_alerts(location_id: int) -> str:
    return f"greenpulse:alerts:{location_id}"

def key_agent_session(session_id: str) -> str:
    return f"greenpulse:agent_session:{session_id}"
