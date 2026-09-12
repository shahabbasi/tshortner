from redis.asyncio import Redis

_CACHE_KEY_PREFIX = "short_url:"


def _cache_key(short_code: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{short_code}"


class URLCache:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, short_code: str) -> str | None:
        return await self._redis.get(_cache_key(short_code))

    async def set(self, short_code: str, long_url: str) -> None:
        await self._redis.set(_cache_key(short_code), long_url, ex=self._ttl_seconds)

    async def invalidate(self, short_code: str) -> None:
        await self._redis.delete(_cache_key(short_code))
