import asyncio
from enum import Enum

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from raspbot.core import exceptions as exc
from raspbot.db.base import BaseORM, engine
from raspbot.settings import settings

# # sqlalchemy.Float is treated as decimal.Decimal, not float.
# # So this is a workaround to stop mypy from complaining.
# # https://github.com/dropbox/sqlalchemy-stubs/issues/178

# from typing import cast
# from sqlalchemy.sql.type_api import TypeEngine

# Float = cast(type[TypeEngine[float]], Float_org)


class PointTypeEnum(Enum):
    """Point type choices."""

    station = "station"
    settlement = "settlement"


class StationCommonMixin(object):
    """Common fields and string representation for models."""

    title: Mapped[str] = mapped_column(String(100), default="")
    yandex_code: Mapped[str | None] = mapped_column(String(100), default=None)

    def __repr__(self):
        """String representation."""
        return f"{self.__class__.__name__} {self.title}"


class PointORM(BaseORM, StationCommonMixin):
    """Point model (settlement or station)."""

    point_type: Mapped[PointTypeEnum]
    station_type: Mapped[str | None] = mapped_column(String(100), default=None)
    latitude: Mapped[Float | None] = mapped_column(Float, default=None)
    longitude: Mapped[Float | None] = mapped_column(Float, default=None)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    region: Mapped["RegionORM"] = relationship("RegionORM", back_populates="points")


class RegionORM(BaseORM, StationCommonMixin):
    """Region model."""

    points: Mapped[list["PointORM"]] = relationship("PointORM", back_populates="region")


class LastUpdatedORM(BaseORM):
    """Update date model registering the datetime when the table was last updated."""

    __tablename__ = "last_updated"

    def __repr__(self):
        """String representation of an ORM Model."""
        return (
            f"<{self.__class__.__name__} "
            f"({self.created_at.strftime(settings.LOG_DT_FMT)})>"
        )


async def create_db_schema():
    """Creates database schema.

    Normally this is handled by alembic migrations (alembic upgrade head).
    Launch this manually only if there are problems with alembic.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(BaseORM.metadata.create_all)
    except SQLAlchemyError as e:
        raise exc.CreateSchemaError(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(create_db_schema())
