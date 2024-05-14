import asyncio

import asyncpg
import pytest_asyncio
from aiodocker import Docker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text

from raspbot.db.base import BaseORM
from raspbot.settings import BASE_DIR, settings

ROOT_DIR = BASE_DIR.parent
TEST_DB_PORT = 35432


def get_test_db_url(
    asyncpg: bool = True,
    user: str = settings.POSTGRES_USER,
    password: str = settings.POSTGRES_PASSWORD,
    host: str = settings.DB_HOST,
    port: int = TEST_DB_PORT,
    db: str = settings.POSTGRES_DB,
) -> str:
    """Get a link for connecting to DB."""
    return (
        f"postgresql{'+asyncpg' if asyncpg else ''}://{user}:{password}"
        f"@{host}:{port}/{db}"
    )


@pytest_asyncio.fixture(scope="session")
async def docker():
    """Docker fixture."""
    docker = Docker()
    yield docker
    await docker.close()


async def wait_for_db_init():
    """Waits for the container to start."""
    while True:
        try:
            db_url = get_test_db_url(asyncpg=False)
            await asyncpg.connect(db_url)
            return True
        except ConnectionError:
            pass

        await asyncio.sleep(1)


@pytest_asyncio.fixture(scope="session")
async def postgres_container(docker):
    """Docker DB container fixture."""
    try:
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

        # Start the container
        await container.start()

        # Wait until the connection to the DB can be established
        await wait_for_db_init()

        # Container is ready, yield it
        yield container

    finally:
        await container.stop()
        await container.delete(force=True)


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container):
    """DB engine fixture."""
    # https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops  # noqa
    engine = create_async_engine(get_test_db_url(), poolclass=NullPool)

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
