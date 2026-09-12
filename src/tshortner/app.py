from fastapi import FastAPI

from tshortner.api.v1.router import api_router
from tshortner.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.include_router(api_router)

    return app


app = create_app()
