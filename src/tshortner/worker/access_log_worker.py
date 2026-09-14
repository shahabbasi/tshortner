import asyncio
import json
import logging
from collections import Counter
from contextlib import suppress
from datetime import datetime

from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.core.config import get_settings
from tshortner.models.access_log import AccessLog
from tshortner.repositories.url_repository import URLRepository
from tshortner.worker.base import BackgroundWorker

logger = logging.getLogger(__name__)


class AccessLogWorker(BackgroundWorker):
    """Buffers access events from Redis pub/sub and periodically saves them as access logs and click counts.

    Pub/sub delivers every event to every instance; each instance keeps only codes that start with one of
    its own prefixes, so with disjoint prefixes every click is saved exactly once. Pub/sub doesn't persist
    messages: events published while no worker is subscribed are lost.
    """

    def __init__(self) -> None:
        super().__init__("worker", get_settings().access_log_flush_interval_seconds)
        self._buffer: list[dict] = []

    async def work(self, session_factory: async_sessionmaker[AsyncSession], redis: Redis) -> None:
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe(get_settings().access_events_channel)
            consumer = asyncio.create_task(self._consume(pubsub))
            while not await self.sleep():
                await self._flush(session_factory)
            consumer.cancel()
            with suppress(asyncio.CancelledError):
                await consumer
        await self._flush(session_factory)

    async def _consume(self, pubsub: PubSub) -> None:
        prefixes = set(get_settings().short_code_prefixes)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event = json.loads(message["data"])
                owned = event["short_code"][:1] in prefixes
            except (ValueError, KeyError, TypeError):
                logger.warning("dropped malformed access event", extra={"data": message["data"]})
                continue
            if owned:
                self._buffer.append(event)
            else:
                logger.debug("ignored access event for another instance's prefix", extra={"short_code": event["short_code"]})

    async def _flush(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        batch, self._buffer = self._buffer, []
        if not batch:
            return
        async with session_factory() as session:
            urls = URLRepository(session)
            ids = await urls.get_ids_by_short_codes({event["short_code"] for event in batch})
            logs = [
                AccessLog(
                    short_url_id=ids[event["short_code"]],
                    ip_address=event["ip_address"],
                    accessed_at=datetime.fromisoformat(event["accessed_at"]),
                )
                for event in batch
                if event["short_code"] in ids
            ]
            if dropped := len(batch) - len(logs):
                logger.warning("dropped access events for unknown short codes", extra={"dropped": dropped})
            session.add_all(logs)
            await urls.increment_click_counts(Counter(event["short_code"] for event in batch))
            await session.commit()
        logger.info("saved access events", extra={"saved": len(logs), "short_codes": len(ids)})
