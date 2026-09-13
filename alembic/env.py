import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

import tshortner.models  # noqa: F401  registers the tables on SQLModel.metadata
from tshortner.core.config import get_settings

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

url = get_settings().postgres_dsn


def run_migrations(**configure_kwargs) -> None:
    context.configure(target_metadata=SQLModel.metadata, **configure_kwargs)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        await connection.run_sync(lambda sync_connection: run_migrations(connection=sync_connection))
    await engine.dispose()


if context.is_offline_mode():
    run_migrations(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
else:
    asyncio.run(run_migrations_online())
