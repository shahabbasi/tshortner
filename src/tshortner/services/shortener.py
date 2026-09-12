from datetime import datetime

from tshortner.models.url import ShortURL
from tshortner.repositories.url_repository import URLRepository
from tshortner.services.cache import URLCache
from tshortner.utils import base62


class URLShortenerService:
    def __init__(self, repository: URLRepository, cache: URLCache) -> None:
        self._repository = repository
        self._cache = cache

    async def shorten(self, long_url: str, user_id: str, expires_at: datetime | None = None) -> ShortURL:
        existing = await self._repository.get_by_user_and_long_url(user_id, long_url)
        if existing is not None:
            return existing

        entry = await self._repository.create(long_url=long_url, user_id=user_id, expires_at=expires_at)
        short_code = base62.encode(entry.id)
        entry.short_code = short_code
        await self._repository.update(entry)
        return entry

    async def resolve(self, short_code: str) -> str | None:
        cached = await self._cache.get(short_code)
        if cached is not None:
            return cached

        entry = await self._repository.get_by_code(short_code)
        if entry is None:
            return None

        await self._cache.set(short_code, entry.long_url)
        await self._repository.increment_click_count(short_code)
        return entry.long_url
