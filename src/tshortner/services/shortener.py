from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError

from tshortner.core.config import get_settings
from tshortner.models.url import ShortURL
from tshortner.repositories.url_repository import URLRepository
from tshortner.utils.short_code import random_short_code

_MAX_CODE_ATTEMPTS = 5


def cache_key(short_code: str) -> str:
    return f"short_url:{short_code}"


class URLShortenerService:
    def __init__(self, repository: URLRepository, redis: Redis) -> None:
        self._repository = repository
        self._redis = redis

    async def shorten(self, original_url: str, user_id: str, expires_at: datetime | None = None) -> ShortURL:
        existing = await self._repository.get_by_user_and_original_url(user_id, original_url)
        if existing is not None:
            return existing

        settings = get_settings()
        for _ in range(_MAX_CODE_ATTEMPTS):
            short_code = random_short_code(settings.short_code_prefixes, settings.short_code_length)
            if await self._repository.code_exists(short_code):
                continue
            try:
                return await self._repository.create(short_code, original_url, user_id, expires_at)
            except IntegrityError:
                # Lost a race: another request took this code, or stored the same URL for this user.
                existing = await self._repository.get_by_user_and_original_url(user_id, original_url)
                if existing is not None:
                    return existing
        raise RuntimeError(f"no unused short code found after {_MAX_CODE_ATTEMPTS} attempts")

    async def resolve(self, short_code: str) -> str | None:
        key = cache_key(short_code)
        if (cached := await self._redis.get(key)) is not None:
            return cached
        entry = await self._repository.get_by_code(short_code)
        if entry is None:
            return None
        await self._redis.set(key, entry.original_url, ex=get_settings().cache_ttl_seconds)
        return entry.original_url

    async def get_open_count(self, short_url_id: int) -> int | None:
        entry = await self._repository.get_by_id(short_url_id)
        return None if entry is None else entry.click_count
