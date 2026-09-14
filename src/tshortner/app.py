from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tshortner.api.request_logging import log_requests
from tshortner.api.v1.router import api_router
from tshortner.core.config import get_settings
from tshortner.core.logging import configure_logging
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


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=_lifespan)
    app.middleware("http")(log_requests)
    app.include_router(api_router)
    return app


app = create_app()
