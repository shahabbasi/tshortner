from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from tshortner.api.v1.router import api_router
from tshortner.core.config import get_settings
from tshortner.db.redis import get_redis
from tshortner.middleware.access_recording import record_short_link_access
from tshortner.worker.access_log_worker import AccessLogWorker
from tshortner.worker.expiry_worker import ExpiryWorker


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    workers = [AccessLogWorker(), ExpiryWorker()]
    for worker in workers:
        worker.start()
    try:
        yield
    finally:
        for worker in workers:
            worker.stop()


def create_app(redis: Redis | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=_lifespan)
    # Middleware sits outside FastAPI's dependency overrides, so tests inject their fake Redis here.
    app.state.redis = redis or get_redis()
    app.middleware("http")(record_short_link_access)
    app.include_router(api_router)
    return app


app = create_app()
