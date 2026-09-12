from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.core.config import get_settings
from tshortner.db.postgres import get_db_session
from tshortner.db.redis import get_redis
from tshortner.repositories.url_repository import URLRepository
from tshortner.services.cache import URLCache
from tshortner.services.shortener import URLShortenerService

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_url_repository(session: SessionDep) -> URLRepository:
    return URLRepository(session)


def get_url_cache(redis: RedisDep) -> URLCache:
    return URLCache(redis, ttl_seconds=get_settings().cache_ttl_seconds)


def get_shortener_service(
    repository: Annotated[URLRepository, Depends(get_url_repository)],
    cache: Annotated[URLCache, Depends(get_url_cache)],
) -> URLShortenerService:
    return URLShortenerService(repository, cache)


ShortenerServiceDep = Annotated[URLShortenerService, Depends(get_shortener_service)]
