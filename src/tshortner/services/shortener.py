import hashlib
import logging
from datetime import datetime
from urllib.parse import urlsplit

from redis.asyncio import Redis
from redis.exceptions import LockError
from sqlalchemy.exc import IntegrityError

from tshortner.core.config import get_settings
from tshortner.models.url import ShortURL
from tshortner.repositories.url_repository import URLRepository
from tshortner.utils.short_code import random_short_code

logger = logging.getLogger(__name__)

_MAX_CODE_ATTEMPTS = 5
# The lease comfortably outlasts a normal create, yet frees the URL soon if its holder dies mid-request.
_LOCK_LEASE_SECONDS = 10
_LOCK_WAIT_SECONDS = 5


class ShortenInProgressError(Exception):
    """Another request for the same URL held its lock for longer than a duplicate waits."""


def cache_key(short_code: str) -> str:
    return f"short_url:{short_code}"


def shorten_lock_key(original_url: str) -> str:
    return f"lock:shorten:{hashlib.sha256(original_url.encode()).hexdigest()}"


class URLShortenerService:
    def __init__(self, repository: URLRepository, redis: Redis) -> None:
        self._repository = repository
        self._redis = redis

    async def shorten(self, original_url: str, user_id: str, expires_at: datetime | None = None) -> ShortURL:
        """Creates one URL at a time across all instances; a duplicate waits, then finds the first request's row."""
        lock = self._redis.lock(
            shorten_lock_key(original_url),
            timeout=_LOCK_LEASE_SECONDS,
            blocking_timeout=_LOCK_WAIT_SECONDS,
            # A lease that ran out mid-create still committed the row, so don't fail the request on release.
            raise_on_release_error=False,
        )
        try:
            async with lock:
                return await self._get_or_create(original_url, user_id, expires_at)
        except LockError as exc:
            logger.warning(
                "gave up waiting for another request shortening the same URL",
                extra={"host": urlsplit(original_url).hostname, "waited_seconds": _LOCK_WAIT_SECONDS},
            )
            raise ShortenInProgressError(original_url) from exc

    async def _get_or_create(self, original_url: str, user_id: str, expires_at: datetime | None) -> ShortURL:
        existing = await self._repository.get_by_user_and_original_url(user_id, original_url)
        if existing is not None:
            logger.info("returned existing short link", extra={"short_code": existing.short_code})
            return existing

        settings = get_settings()
        for attempt in range(1, _MAX_CODE_ATTEMPTS + 1):
            short_code = random_short_code(settings.short_code_prefixes, settings.short_code_length)
            if await self._repository.code_exists(short_code):
                logger.debug("generated code is taken, retrying", extra={"short_code": short_code, "attempt": attempt})
                continue
            try:
                entry = await self._repository.create(short_code, original_url, user_id, expires_at)
            except IntegrityError:
                # Lost a race: another request took this code, or stored the same URL for this user.
                existing = await self._repository.get_by_user_and_original_url(user_id, original_url)
                if existing is not None:
                    logger.info("returned short link stored by a concurrent request", extra={"short_code": existing.short_code})
                    return existing
                logger.warning(
                    "generated code was taken by a concurrent request, retrying",
                    extra={"short_code": short_code, "attempt": attempt},
                )
                continue
            logger.info("created short link", extra={"short_code": short_code, "host": urlsplit(original_url).hostname})
            return entry
        raise RuntimeError(f"no unused short code found after {_MAX_CODE_ATTEMPTS} attempts")

    async def resolve(self, short_code: str) -> str | None:
        key = cache_key(short_code)
        ttl = get_settings().cache_ttl_seconds
        # GETEX resets the TTL on every hit, so a link stays cached until it goes unused for a full TTL.
        if (cached := await self._redis.getex(key, ex=ttl)) is not None:
            logger.debug("cache hit", extra={"short_code": short_code})
            return cached
        entry = await self._repository.get_by_code(short_code)
        if entry is None:
            logger.debug("unknown short code", extra={"short_code": short_code})
            return None
        await self._redis.set(key, entry.original_url, ex=ttl)
        logger.debug("cache miss, cached the original URL", extra={"short_code": short_code})
        return entry.original_url

    async def get_stats(self, short_url_id: int) -> tuple[str, int] | None:
        """Returns the link's short code and open count; once expired, the code it had is in expired_short_code."""
        entry = await self._repository.get_by_id(short_url_id)
        if entry is None:
            return None
        return entry.short_code or entry.expired_short_code, entry.click_count
