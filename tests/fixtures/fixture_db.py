import asyncio

import pytest_asyncio
from aiodocker import Docker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text

from raspbot.db.base import BaseORM
from raspbot.settings import BASE_DIR, settings

ROOT_DIR = BASE_DIR.parent
TEST_DB_PORT = 35432
TEST_DB_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.DB_HOST}:{TEST_DB_PORT}/{settings.POSTGRES_DB}"
)


@pytest_asyncio.fixture(scope="session")
async def docker():
    """Docker fixture."""
    docker = Docker()
    yield docker
    await docker.close()


@pytest_asyncio.fixture(scope="session")
async def postgres_container(docker):
    """Docker DB container fixture."""
    container = await docker.containers.create_or_replace(
        name="postgres",
        config={
            "Image": "postgres:16.1-alpine",
            "Env": [
                f"POSTGRES_DB={settings.POSTGRES_DB}",
                f"POSTGRES_USER={settings.POSTGRES_USER}",
                f"POSTGRES_PASSWORD={settings.POSTGRES_PASSWORD}",
                f"LC_COLLATE={settings.LC_COLLATE}",
                f"LC_CTYPE={settings.LC_CTYPE}",
            ],
            "HostConfig": {
                "PortBindings": {"5432/tcp": [{"HostPort": str(TEST_DB_PORT)}]}
            },
        },
    )

    await container.start()
    await asyncio.sleep(5)
    yield container
    await container.stop()
    await container.delete(force=True)


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container):
    """DB engine fixture."""
    # https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops  # noqa
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(BaseORM.metadata.drop_all)
        await conn.run_sync(BaseORM.metadata.create_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine):
    """Session fixture."""
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
