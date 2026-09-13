import asyncio
import threading
from contextlib import suppress

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.core.config import get_settings


class BackgroundWorker:
    """Runs `work()` on a dedicated thread and event loop with its own Postgres and Redis connections.

    asyncpg and redis.asyncio connections are bound to the loop that created them, so they can't be
    shared with the app's loop.
    """

    def __init__(self, name: str, interval_seconds: float) -> None:
        self._interval_seconds = interval_seconds
        self._loop = asyncio.new_event_loop()
        self._stop = asyncio.Event()
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(self._stop.set)
        self._thread.join(timeout=10)

    async def sleep(self) -> bool:
        """Waits one interval, returning early with True once stop() is called."""
        with suppress(TimeoutError):
            await asyncio.wait_for(self._stop.wait(), self._interval_seconds)
        return self._stop.is_set()

    async def work(self, session_factory: async_sessionmaker[AsyncSession], redis: Redis) -> None:
        raise NotImplementedError

    def _run(self) -> None:
        try:
            self._loop.run_until_complete(self._main())
        finally:
            self._loop.close()

    async def _main(self) -> None:
        settings = get_settings()
        engine = create_async_engine(settings.postgres_dsn)
        redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
        try:
            await self.work(async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False), redis)
        finally:
            await redis.aclose()
            await engine.dispose()
