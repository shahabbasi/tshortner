from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.api.deps import get_db_session, get_redis
from tshortner.app import create_app
from tshortner.repositories.url_repository import URLRepository
from tshortner.services.cache import URLCache
from tshortner.services.shortener import URLShortenerService


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[FakeAsyncRedis, None]:
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def url_repository(db_session: AsyncSession) -> URLRepository:
    return URLRepository(db_session)


@pytest.fixture
def url_cache(fake_redis: FakeAsyncRedis) -> URLCache:
    return URLCache(fake_redis, ttl_seconds=3600)


@pytest.fixture
def shortener_service(url_repository: URLRepository, url_cache: URLCache) -> URLShortenerService:
    return URLShortenerService(url_repository, url_cache)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, fake_redis: FakeAsyncRedis) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _get_db_session_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _get_redis_override() -> AsyncGenerator[FakeAsyncRedis, None]:
        yield fake_redis

    app.dependency_overrides[get_db_session] = _get_db_session_override
    app.dependency_overrides[get_redis] = _get_redis_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
