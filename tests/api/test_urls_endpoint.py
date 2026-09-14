import pytest
from fakeredis import FakeAsyncRedis
from httpx import AsyncClient

from tshortner.services.shortener import shorten_lock_key


async def _shorten(client: AsyncClient, original_url: str = "https://example.com/a", user_id: str = "user-1") -> dict:
    response = await client.post("/urls", json={"original_url": original_url, "user_id": user_id})
    assert response.status_code == 201
    return response.json()


async def test_shorten_and_redirect(client: AsyncClient) -> None:
    body = await _shorten(client, "https://example.com/a/very/long/path")
    assert body["original_url"] == "https://example.com/a/very/long/path"
    assert body["short_url"] == f"http://testserver/{body['short_code']}"

    response = await client.get(f"/{body['short_code']}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/a/very/long/path"


async def test_redirect_unknown_code_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/does-not-exist")).status_code == 404


async def test_shorten_missing_user_id_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/urls", json={"original_url": "https://example.com/a"})

    assert response.status_code == 422


async def test_shorten_reuses_code_only_for_same_user(client: AsyncClient) -> None:
    code = (await _shorten(client))["short_code"]

    assert (await _shorten(client))["short_code"] == code
    assert (await _shorten(client, user_id="user-2"))["short_code"] != code


async def test_shorten_returns_409_when_the_url_stays_locked(
    client: AsyncClient, fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tshortner.services.shortener._LOCK_WAIT_SECONDS", 0.2)
    await fake_redis.lock(shorten_lock_key("https://example.com/a"), timeout=10).acquire()

    response = await client.post("/urls", json={"original_url": "https://example.com/a", "user_id": "user-1"})

    assert response.status_code == 409
    assert response.headers["retry-after"] == "1"


async def test_get_stats(client: AsyncClient) -> None:
    created = await _shorten(client)

    response = await client.get(f"/urls/{created['id']}/stats")

    assert response.status_code == 200
    assert response.json() == {"short_url_id": created["id"], "short_code": created["short_code"], "open_count": 0}
    assert (await client.get("/urls/999999/stats")).status_code == 404
