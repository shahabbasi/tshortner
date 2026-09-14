import logging

import pytest
from fastapi import FastAPI
from httpx import AsyncClient


def _request_logs(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == "tshortner.request"]


async def test_each_request_gets_an_id_and_one_summary_line(client: AsyncClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        response = await client.get("/health")

    [record] = _request_logs(caplog)
    assert (record.method, record.path, record.status, record.client_ip) == ("GET", "/health", 200, "127.0.0.1")
    assert record.duration_ms >= 0
    assert record.request_id == response.headers["x-request-id"]
    assert len(record.request_id) == 32


async def test_safe_incoming_request_id_is_kept_and_unsafe_one_replaced(client: AsyncClient) -> None:
    kept = await client.get("/health", headers={"X-Request-ID": "trace-123"})
    replaced = await client.get("/health", headers={"X-Request-ID": "not safe; <script>"})

    assert kept.headers["x-request-id"] == "trace-123"
    assert len(replaced.headers["x-request-id"]) == 32


async def test_logs_written_during_a_request_carry_its_id(client: AsyncClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        response = await client.post("/urls", json={"original_url": "https://example.com/a?token=secret", "user_id": "user-1"})

    created = next(record for record in caplog.records if record.getMessage() == "created short link")
    assert created.request_id == response.headers["x-request-id"]
    assert (created.short_code, created.host) == (response.json()["short_code"], "example.com")
    assert "secret" not in caplog.text


async def test_unhandled_error_is_logged_with_traceback_and_returns_500(
    app: FastAPI, client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/boom/now")
    async def boom() -> None:
        raise RuntimeError("boom")

    with caplog.at_level(logging.INFO):
        response = await client.get("/boom/now")

    [record] = _request_logs(caplog)
    assert response.status_code == 500
    assert (record.levelno, record.status, record.getMessage()) == (logging.ERROR, 500, "request failed")
    assert record.exc_info is not None
    assert record.request_id == response.headers["x-request-id"]
