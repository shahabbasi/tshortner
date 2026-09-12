import pytest

from tshortner.repositories.url_repository import URLRepository

pytestmark = pytest.mark.asyncio


async def test_create_and_get_by_code(url_repository: URLRepository) -> None:
    created = await url_repository.create(long_url="https://example.com/a", user_id="user-1")
    created.short_code = "abc123"
    await url_repository.update(created)

    fetched = await url_repository.get_by_code("abc123")

    assert fetched is not None
    assert fetched.long_url == "https://example.com/a"


async def test_get_by_code_missing_returns_none(url_repository: URLRepository) -> None:
    assert await url_repository.get_by_code("missing") is None


async def test_get_by_user_and_long_url(url_repository: URLRepository) -> None:
    await url_repository.create(long_url="https://example.com/a", user_id="user-1", short_code="abc123")

    fetched = await url_repository.get_by_user_and_long_url("user-1", "https://example.com/a")

    assert fetched is not None
    assert fetched.short_code == "abc123"


async def test_get_by_user_and_long_url_scoped_to_user(url_repository: URLRepository) -> None:
    await url_repository.create(long_url="https://example.com/a", user_id="user-1", short_code="abc123")

    fetched = await url_repository.get_by_user_and_long_url("user-2", "https://example.com/a")

    assert fetched is None


async def test_increment_click_count(url_repository: URLRepository) -> None:
    entry = await url_repository.create(long_url="https://example.com/a", user_id="user-1", short_code="abc123")
    assert entry.click_count == 0

    await url_repository.increment_click_count("abc123")

    fetched = await url_repository.get_by_code("abc123")
    assert fetched is not None
    assert fetched.click_count == 1
