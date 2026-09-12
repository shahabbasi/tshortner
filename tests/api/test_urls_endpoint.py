import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["postgres"] == {"status": "ok", "error": None}
    assert body["redis"] == {"status": "ok", "error": None}


async def test_shorten_and_redirect(client: AsyncClient) -> None:
    create_response = await client.post(
        "/urls", json={"long_url": "https://example.com/a/very/long/path", "user_id": "user-1"}
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["long_url"] == "https://example.com/a/very/long/path"
    short_code = body["short_code"]

    redirect_response = await client.get(f"/{short_code}", follow_redirects=False)

    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "https://example.com/a/very/long/path"


async def test_redirect_unknown_code_returns_404(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist")

    assert response.status_code == 404


async def test_shorten_missing_user_id_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/urls", json={"long_url": "https://example.com/a"})

    assert response.status_code == 422


async def test_shorten_same_user_same_url_returns_same_code(client: AsyncClient) -> None:
    payload = {"long_url": "https://example.com/a", "user_id": "user-1"}

    first = await client.post("/urls", json=payload)
    second = await client.post("/urls", json=payload)

    assert first.json()["short_code"] == second.json()["short_code"]


async def test_shorten_different_users_same_url_get_different_codes(client: AsyncClient) -> None:
    first = await client.post("/urls", json={"long_url": "https://example.com/a", "user_id": "user-1"})
    second = await client.post("/urls", json={"long_url": "https://example.com/a", "user_id": "user-2"})

    assert first.json()["short_code"] != second.json()["short_code"]
