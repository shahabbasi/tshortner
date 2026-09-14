import logging
from collections.abc import Awaitable

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from tshortner.api.deps import RedisDep, SessionDep

logger = logging.getLogger(__name__)

router = APIRouter()


class ComponentStatus(BaseModel):
    status: str
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    postgres: ComponentStatus
    redis: ComponentStatus


async def _check(component: str, probe: Awaitable[object]) -> ComponentStatus:
    try:
        await probe
    except Exception as exc:
        logger.warning("health check failed", extra={"component": component, "error": str(exc)})
        return ComponentStatus(status="error", error=str(exc))
    return ComponentStatus(status="ok")


@router.get("/health")
async def health_check(response: Response, session: SessionDep, redis: RedisDep) -> HealthResponse:
    postgres_status = await _check("postgres", session.exec(text("SELECT 1")))
    redis_status = await _check("redis", redis.ping())
    healthy = postgres_status.status == redis_status.status == "ok"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="ok" if healthy else "error", postgres=postgres_status, redis=redis_status)
