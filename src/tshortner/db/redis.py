from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from tshortner.core.config import get_settings

_redis: Redis | None = None


def get_redis_client() -> Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    return _redis


async def get_redis() -> AsyncGenerator[Redis, None]:
    yield get_redis_client()
