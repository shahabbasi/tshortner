import pytest
from httpx import ASGITransport, AsyncClient

from tshortner.api.deps import get_db_session, get_redis
from tshortner.app import create_app

pytestmark = pytest.mark.asyncio


class _BrokenSession:
    async def exec(self, *args, **kwargs):
        raise RuntimeError("db down")


class _BrokenRedis:
    async def ping(self) -> None:
        raise ConnectionError("redis down")


async def test_health_check_reports_error_when_dependencies_fail() -> None:
    app = create_app()

    async def _broken_db_session():
        yield _BrokenSession()

    async def _broken_redis():
        yield _BrokenRedis()

    app.dependency_overrides[get_db_session] = _broken_db_session
    app.dependency_overrides[get_redis] = _broken_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["postgres"] == {"status": "error", "error": "db down"}
    assert body["redis"] == {"status": "error", "error": "redis down"}
