import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.core.config import get_settings
from tshortner.repositories.url_repository import URLRepository
from tshortner.services.shortener import cache_key
from tshortner.worker.base import BackgroundWorker

logger = logging.getLogger(__name__)


class ExpiryWorker(BackgroundWorker):
    """Archives expired short URLs on startup and then every interval (every 5 minutes by default)."""

    def __init__(self) -> None:
        super().__init__("expiry-worker", get_settings().expiry_check_interval_seconds)

    async def work(self, session_factory: async_sessionmaker[AsyncSession], redis: Redis) -> None:
        while True:
            async with session_factory() as session:
                codes = await URLRepository(session).archive_expired(datetime.now(timezone.utc))
                await session.commit()
            if codes:
                # Otherwise a cached code keeps redirecting until its TTL runs out.
                await redis.delete(*map(cache_key, codes))
                logger.info("archived expired short links", extra={"archived": len(codes)})
            if await self.sleep():
                return
