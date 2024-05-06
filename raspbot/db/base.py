import logging
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import DateTime, func
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
    """Describes table name and fields that should be present in all models."""

    @declared_attr
    def __tablename__(cls):
        """Returns table name based on the name of the ORM class."""
        snake_string = ""
        no_orm = cls.__name__.replace("ORM", "s")
        for index, char in enumerate(no_orm):
            if char.isupper() and index != 0:
                snake_string += "_"
            snake_string += char.lower()
        return snake_string

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    repr_exclude_cols = ("created_at", "updated_at")

    def __repr__(self):
        """String representation of an ORM Model."""
        cols = []
        for col in self.__table__.columns.keys():
            if col not in self.repr_exclude_cols:
                cols.append(f"{col}={getattr(self, col)}")

        return f"<{self.__class__.__name__} ({', '.join(cols)})>"


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
