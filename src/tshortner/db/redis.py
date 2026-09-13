from functools import lru_cache

from redis.asyncio import Redis

from tshortner.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_dsn, decode_responses=True)
