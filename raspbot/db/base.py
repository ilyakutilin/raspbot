import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from raspbot.core.logging import configure_logging
from raspbot.settings import settings

logger = configure_logging(name="sqlalchemy.engine", level=logging.INFO)


class PreBaseORM:
    """Describes table name and id field that should be present in all models."""

    @declared_attr
    def __tablename__(cls):
        """Returns table name based on the name of the ORM class."""
        return cls.__name__.lower().replace("orm", "s")

    id: Mapped[int] = mapped_column(primary_key=True)


class BaseORM(AsyncAttrs, DeclarativeBase, PreBaseORM):
    """Base class for all models. All models shall be inherited from this class."""

    pass


engine = create_async_engine(settings.database_url)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get the DB session."""
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
