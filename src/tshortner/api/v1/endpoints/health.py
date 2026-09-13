from collections.abc import Awaitable

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from tshortner.api.deps import RedisDep, SessionDep

router = APIRouter()


class ComponentStatus(BaseModel):
    status: str
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    postgres: ComponentStatus
    redis: ComponentStatus


async def _check(probe: Awaitable[object]) -> ComponentStatus:
    try:
        await probe
    except Exception as exc:
        return ComponentStatus(status="error", error=str(exc))
    return ComponentStatus(status="ok")


@router.get("/health")
async def health_check(response: Response, session: SessionDep, redis: RedisDep) -> HealthResponse:
    postgres_status = await _check(session.exec(text("SELECT 1")))
    redis_status = await _check(redis.ping())
    healthy = postgres_status.status == redis_status.status == "ok"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="ok" if healthy else "error", postgres=postgres_status, redis=redis_status)
