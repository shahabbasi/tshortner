import asyncio
import json

import pytest
from fakeredis import FakeAsyncRedis

from tshortner.core.config import get_settings
from tshortner.worker.access_log_worker import AccessLogWorker


async def test_worker_keeps_only_events_for_its_own_prefixes(
    fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "short_code_prefixes", ["a", "b"])
    channel = get_settings().access_events_channel
    worker = AccessLogWorker()
    try:
        async with fake_redis.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            consumer = asyncio.create_task(worker._consume(pubsub))
            for message in ["not json", json.dumps({"ip_address": "no code"})] + [
                json.dumps({"short_code": code, "ip_address": "203.0.113.1", "accessed_at": "2026-09-13T12:00:00+00:00"})
                for code in ["aOwned1", "Zforeign", "COTHER1", "bOwned2"]
            ]:
                await fake_redis.publish(channel, message)

            # Events arrive in order, so once the last owned event is buffered every earlier one was handled.
            async with asyncio.timeout(2):
                while not worker._buffer or worker._buffer[-1]["short_code"] != "bOwned2":
                    await asyncio.sleep(0.01)
            consumer.cancel()

        assert [event["short_code"] for event in worker._buffer] == ["aOwned1", "bOwned2"]
    finally:
        worker._loop.close()
