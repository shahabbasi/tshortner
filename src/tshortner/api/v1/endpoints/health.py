from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.api.deps import RedisDep, SessionDep

router = APIRouter()


class ComponentStatus(BaseModel):
    status: str
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    postgres: ComponentStatus
    redis: ComponentStatus


async def _check_postgres(session: AsyncSession) -> ComponentStatus:
    try:
        await session.exec(text("SELECT 1"))
        return ComponentStatus(status="ok")
    except Exception as exc:
        return ComponentStatus(status="error", error=str(exc))


async def _check_redis(redis: Redis) -> ComponentStatus:
    try:
        await redis.ping()
        return ComponentStatus(status="ok")
    except Exception as exc:
        return ComponentStatus(status="error", error=str(exc))


@router.get("/health", response_model=HealthResponse)
async def health_check(response: Response, session: SessionDep, redis: RedisDep) -> HealthResponse:
    postgres_status = await _check_postgres(session)
    redis_status = await _check_redis(redis)

    is_healthy = postgres_status.status == "ok" and redis_status.status == "ok"
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if is_healthy else "error",
        postgres=postgres_status,
        redis=redis_status,
    )
