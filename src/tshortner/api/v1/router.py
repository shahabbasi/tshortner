from fastapi import APIRouter

from tshortner.api.v1.endpoints import health, urls

api_router = APIRouter()
# health must be included before urls: urls exposes a catch-all GET /{short_code}
# redirect route that would otherwise shadow /health.
api_router.include_router(health.router, tags=["health"])
api_router.include_router(urls.router, tags=["urls"])
