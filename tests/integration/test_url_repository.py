from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from tshortner.models.url import ShortURL
from tshortner.repositories.url_repository import URLRepository

URL_A = "https://example.com/a"
URL_B = "https://example.com/b"


async def _reload(url_repository: URLRepository, entry_id: int) -> ShortURL:
    """Reads the persisted row rather than the session's cached copy, which bulk updates leave stale."""
    query = select(ShortURL).where(ShortURL.id == entry_id).execution_options(populate_existing=True)
    return (await url_repository._session.exec(query)).one()


async def test_create_and_lookups(url_repository: URLRepository) -> None:
    entry = await url_repository.create("abc1234", URL_A, "user-1")

    assert (await url_repository.get_by_code("abc1234")).id == entry.id
    assert (await url_repository.get_by_id(entry.id)).short_code == "abc1234"
    assert await url_repository.get_by_code("missing") is None
    assert await url_repository.get_by_id(999999) is None


async def test_create_rejects_taken_code_and_leaves_session_usable(url_repository: URLRepository) -> None:
    await url_repository.create("abc1234", URL_A, "user-1")

    with pytest.raises(IntegrityError):
        await url_repository.create("abc1234", URL_B, "user-1")

    assert await url_repository.code_exists("abc1234")


async def test_code_exists_covers_active_and_expired_codes(url_repository: URLRepository) -> None:
    now = datetime.now(timezone.utc)
    await url_repository.create("active1", URL_A, "user-1")
    await url_repository.create("expired", URL_B, "user-1", now - timedelta(days=1))
    await url_repository.archive_expired(now)
    await url_repository._session.commit()

    assert await url_repository.code_exists("active1")
    assert await url_repository.code_exists("expired")
    assert not await url_repository.code_exists("unused1")


async def test_get_by_user_and_original_url_is_scoped_to_user(url_repository: URLRepository) -> None:
    entry = await url_repository.create("abc1234", URL_A, "user-1")

    assert (await url_repository.get_by_user_and_original_url("user-1", URL_A)).id == entry.id
    assert await url_repository.get_by_user_and_original_url("user-2", URL_A) is None


async def test_get_ids_by_short_codes(url_repository: URLRepository) -> None:
    a = await url_repository.create("aaaaaaa", URL_A, "user-1")
    b = await url_repository.create("bbbbbbb", URL_B, "user-1")

    assert await url_repository.get_ids_by_short_codes(["aaaaaaa", "bbbbbbb", "missing"]) == {
        "aaaaaaa": a.id,
        "bbbbbbb": b.id,
    }


async def test_increment_click_counts_accumulates(url_repository: URLRepository) -> None:
    a = await url_repository.create("aaaaaaa", URL_A, "user-1")
    b = await url_repository.create("bbbbbbb", URL_B, "user-1")

    await url_repository.increment_click_counts({"aaaaaaa": 2, "bbbbbbb": 1})
    await url_repository.increment_click_counts({"aaaaaaa": 5})
    await url_repository._session.commit()

    assert (await _reload(url_repository, a.id)).click_count == 7
    assert (await _reload(url_repository, b.id)).click_count == 1


async def test_archive_expired_moves_only_expired_codes_and_keeps_rows(url_repository: URLRepository) -> None:
    now = datetime.now(timezone.utc)
    expired = await url_repository.create("expired", "https://example.com/old", "user-1", now - timedelta(days=1))
    await url_repository.create("future1", "https://example.com/new", "user-1", now + timedelta(days=1))
    await url_repository.create("forever", "https://example.com/forever", "user-1")
    await url_repository.increment_click_counts({"expired": 3})

    assert await url_repository.archive_expired(now) == ["expired"]
    await url_repository._session.commit()

    archived = await _reload(url_repository, expired.id)
    assert (archived.short_code, archived.expired_short_code, archived.click_count) == (None, "expired", 3)
    assert await url_repository.get_by_code("expired") is None
    assert await url_repository.get_by_code("future1") is not None
    assert await url_repository.get_by_code("forever") is not None
    assert await url_repository.archive_expired(now) == []
