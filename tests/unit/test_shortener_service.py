import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis

from tshortner.core.config import get_settings
from tshortner.repositories.url_repository import URLRepository
from tshortner.services.shortener import ShortenInProgressError, URLShortenerService, cache_key, shorten_lock_key

URL_A = "https://example.com/a"
URL_B = "https://example.com/b"


def _fix_codes(monkeypatch: pytest.MonkeyPatch, *codes: str) -> None:
    generated = iter(codes)
    monkeypatch.setattr("tshortner.services.shortener.random_short_code", lambda *_: next(generated))


async def test_shorten_uses_this_instances_prefixes(
    shortener_service: URLShortenerService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "short_code_prefixes", ["x", "Y"])

    entry = await shortener_service.shorten(URL_A, "user-1")

    assert (entry.original_url, entry.user_id) == (URL_A, "user-1")
    assert entry.short_code[0] in {"x", "Y"}
    assert len(entry.short_code) == get_settings().short_code_length


async def test_shorten_reuses_code_only_for_same_user_and_url(shortener_service: URLShortenerService) -> None:
    code = (await shortener_service.shorten(URL_A, "user-1")).short_code

    assert (await shortener_service.shorten(URL_A, "user-1")).short_code == code
    assert (await shortener_service.shorten(URL_A, "user-2")).short_code != code
    assert (await shortener_service.shorten(URL_B, "user-1")).short_code != code


async def test_shorten_skips_active_and_expired_codes(
    shortener_service: URLShortenerService, url_repository: URLRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(timezone.utc)
    await url_repository.create("active1", URL_A, "user-1")
    await url_repository.create("expired", URL_B, "user-1", now - timedelta(days=1))
    await url_repository.archive_expired(now)
    await url_repository._session.commit()
    _fix_codes(monkeypatch, "active1", "expired", "fresh01")

    entry = await shortener_service.shorten("https://example.com/c", "user-1")

    assert entry.short_code == "fresh01"


async def test_shorten_retries_when_code_is_taken_between_check_and_insert(
    shortener_service: URLShortenerService, url_repository: URLRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    await url_repository.create("taken01", URL_A, "user-1")
    monkeypatch.setattr(url_repository, "code_exists", AsyncMock(return_value=False))
    _fix_codes(monkeypatch, "taken01", "fresh01")

    assert (await shortener_service.shorten(URL_B, "user-1")).short_code == "fresh01"


async def test_shorten_returns_row_stored_by_concurrent_request(
    shortener_service: URLShortenerService, url_repository: URLRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    await url_repository.create("stored1", URL_A, "user-1")
    real_lookup = url_repository.get_by_user_and_original_url
    calls = 0

    async def racy_lookup(user_id: str, original_url: str):
        # The first lookup misses the concurrent request's row, so the insert then conflicts on it.
        nonlocal calls
        calls += 1
        return None if calls == 1 else await real_lookup(user_id, original_url)

    monkeypatch.setattr(url_repository, "get_by_user_and_original_url", racy_lookup)

    assert (await shortener_service.shorten(URL_A, "user-1")).short_code == "stored1"


async def test_duplicate_request_waits_for_the_lock_then_returns_the_first_requests_row(
    shortener_service: URLShortenerService, url_repository: URLRepository, fake_redis: FakeAsyncRedis
) -> None:
    in_flight = fake_redis.lock(shorten_lock_key(URL_A), timeout=10)
    await in_flight.acquire()

    duplicate = asyncio.create_task(shortener_service.shorten(URL_A, "user-1"))
    await asyncio.sleep(0.3)
    assert not duplicate.done()

    await url_repository.create("first01", URL_A, "user-1")  # the in-flight request finishes
    await in_flight.release()

    assert (await duplicate).short_code == "first01"
    assert not await fake_redis.exists(shorten_lock_key(URL_A))


async def test_duplicate_request_gives_up_when_the_lock_is_held_too_long(
    shortener_service: URLShortenerService, fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tshortner.services.shortener._LOCK_WAIT_SECONDS", 0.2)
    await fake_redis.lock(shorten_lock_key(URL_A), timeout=10).acquire()

    with pytest.raises(ShortenInProgressError):
        await shortener_service.shorten(URL_A, "user-1")


async def test_resolve_returns_none_for_unknown_code(shortener_service: URLShortenerService) -> None:
    assert await shortener_service.resolve("doesnotexist") is None


async def test_resolve_caches_url_for_five_minutes_and_each_hit_resets_the_ttl(
    shortener_service: URLShortenerService, fake_redis: FakeAsyncRedis
) -> None:
    code = (await shortener_service.shorten(URL_A, "user-1")).short_code
    key = cache_key(code)

    assert await shortener_service.resolve(code) == URL_A
    assert await fake_redis.get(key) == URL_A
    assert 295 <= await fake_redis.ttl(key) <= 300

    await fake_redis.expire(key, 10)
    assert await shortener_service.resolve(code) == URL_A
    assert 295 <= await fake_redis.ttl(key) <= 300


async def test_get_open_count(shortener_service: URLShortenerService) -> None:
    entry = await shortener_service.shorten(URL_A, "user-1")

    assert await shortener_service.get_open_count(entry.id) == 0
    assert await shortener_service.get_open_count(999999) is None
