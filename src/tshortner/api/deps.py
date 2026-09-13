from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.db.postgres import get_db_session
from tshortner.db.redis import get_redis
from tshortner.repositories.url_repository import URLRepository
from tshortner.services.shortener import URLShortenerService

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_shortener_service(session: SessionDep, redis: RedisDep) -> URLShortenerService:
    return URLShortenerService(URLRepository(session), redis)


ShortenerServiceDep = Annotated[URLShortenerService, Depends(get_shortener_service)]
