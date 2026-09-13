import json
from datetime import datetime

from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from httpx import AsyncClient

from tshortner.core.config import get_settings


async def _subscribe(fake_redis: FakeAsyncRedis):
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(get_settings().access_events_channel)
    await pubsub.get_message(timeout=1)  # the subscribe confirmation
    return pubsub


async def test_successful_redirect_publishes_access_event(client: AsyncClient, fake_redis: FakeAsyncRedis) -> None:
    response = await client.post("/urls", json={"original_url": "https://example.com/a", "user_id": "user-1"})
    short_code = response.json()["short_code"]
    pubsub = await _subscribe(fake_redis)

    await client.get(f"/{short_code}", follow_redirects=False)

    event = json.loads((await pubsub.get_message(timeout=1))["data"])
    assert (event["short_code"], event["ip_address"]) == (short_code, "127.0.0.1")
    assert datetime.fromisoformat(event["accessed_at"]).tzinfo is not None


async def test_other_requests_do_not_publish(client: AsyncClient, fake_redis: FakeAsyncRedis) -> None:
    pubsub = await _subscribe(fake_redis)

    assert (await client.get("/does-not-exist")).status_code == 404
    await client.get("/health")
    await client.post("/urls", json={"original_url": "https://example.com/b", "user_id": "user-1"})

    assert await pubsub.get_message(timeout=0.5) is None


async def test_injected_parameters_stay_out_of_the_api_schema(app: FastAPI) -> None:
    parameters = app.openapi()["paths"]["/{short_code}"]["get"]["parameters"]

    assert [parameter["name"] for parameter in parameters] == ["short_code"]
