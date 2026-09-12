import pytest

from tshortner.services.shortener import URLShortenerService

pytestmark = pytest.mark.asyncio


async def test_shorten_creates_new_entry(shortener_service: URLShortenerService) -> None:
    entry = await shortener_service.shorten("https://example.com/a", user_id="user-1")

    assert entry.short_code
    assert entry.long_url == "https://example.com/a"
    assert entry.user_id == "user-1"


async def test_shorten_is_idempotent_for_same_user_and_url(shortener_service: URLShortenerService) -> None:
    first = await shortener_service.shorten("https://example.com/a", user_id="user-1")
    second = await shortener_service.shorten("https://example.com/a", user_id="user-1")

    assert first.short_code == second.short_code


async def test_shorten_gives_distinct_codes_to_different_users_for_same_url(
    shortener_service: URLShortenerService,
) -> None:
    first = await shortener_service.shorten("https://example.com/a", user_id="user-1")
    second = await shortener_service.shorten("https://example.com/a", user_id="user-2")

    assert first.short_code != second.short_code


async def test_shorten_produces_distinct_codes_for_distinct_urls(shortener_service: URLShortenerService) -> None:
    first = await shortener_service.shorten("https://example.com/a", user_id="user-1")
    second = await shortener_service.shorten("https://example.com/b", user_id="user-1")

    assert first.short_code != second.short_code


async def test_resolve_returns_none_for_unknown_code(shortener_service: URLShortenerService) -> None:
    assert await shortener_service.resolve("doesnotexist") is None


async def test_resolve_returns_long_url_and_populates_cache(shortener_service: URLShortenerService) -> None:
    entry = await shortener_service.shorten("https://example.com/a", user_id="user-1")

    resolved = await shortener_service.resolve(entry.short_code)

    assert resolved == "https://example.com/a"
    cached = await shortener_service._cache.get(entry.short_code)
    assert cached == "https://example.com/a"
