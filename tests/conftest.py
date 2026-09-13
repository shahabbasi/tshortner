from collections.abc import AsyncIterator

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.api.deps import get_db_session, get_redis
from tshortner.app import create_app
from tshortner.repositories.url_repository import URLRepository
from tshortner.services.shortener import URLShortenerService


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def fake_redis() -> AsyncIterator[FakeAsyncRedis]:
    async with FakeAsyncRedis(decode_responses=True) as client:
        yield client


@pytest.fixture
def url_repository(db_session: AsyncSession) -> URLRepository:
    return URLRepository(db_session)


@pytest.fixture
def shortener_service(url_repository: URLRepository, fake_redis: FakeAsyncRedis) -> URLShortenerService:
    return URLShortenerService(url_repository, fake_redis)


@pytest.fixture
def app(db_session: AsyncSession, fake_redis: FakeAsyncRedis) -> FastAPI:
    app = create_app(redis=fake_redis)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
