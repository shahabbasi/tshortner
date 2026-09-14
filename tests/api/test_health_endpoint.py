import logging

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tshortner.api.deps import get_db_session, get_redis

OK = {"status": "ok", "error": None}


class _BrokenSession:
    async def exec(self, *args: object) -> None:
        raise RuntimeError("db down")


class _BrokenRedis:
    async def ping(self) -> None:
        raise ConnectionError("redis down")


async def test_health_check_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "postgres": OK, "redis": OK}


async def test_health_check_reports_failing_dependencies(
    app: FastAPI, client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    app.dependency_overrides[get_db_session] = _BrokenSession
    app.dependency_overrides[get_redis] = _BrokenRedis

    with caplog.at_level(logging.WARNING):
        response = await client.get("/health")

    failures = {record.component: record.error for record in caplog.records if record.getMessage() == "health check failed"}
    assert failures == {"postgres": "db down", "redis": "redis down"}

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "postgres": {"status": "error", "error": "db down"},
        "redis": {"status": "error", "error": "redis down"},
    }
