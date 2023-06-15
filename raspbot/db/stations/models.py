import asyncio
from datetime import datetime
from enum import Enum
from typing import cast

from sqlalchemy import DateTime
from sqlalchemy import Float as Float_org
from sqlalchemy import ForeignKey, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.type_api import TypeEngine

from raspbot.core import exceptions as exc
from raspbot.db.base import Base, engine

# sqlalchemy.Float is treated as decimal.Decimal, not float.
# So this is a workaround to stop mypy from complaining.
# https://github.com/dropbox/sqlalchemy-stubs/issues/178
Float = cast(type[TypeEngine[float]], Float_org)


class PointTypeEnum(Enum):
    station = "station"
    settlement = "settlement"


class StationCommonMixin(object):
    title: Mapped[str] = mapped_column(String(100), default="")
    yandex_code: Mapped[str | None] = mapped_column(String(100), default=None)

    def __repr__(self):
        return f"{self.__class__.__name__} {self.title}"


class Point(Base, StationCommonMixin):
    point_type: Mapped[PointTypeEnum]
    station_type: Mapped[str | None] = mapped_column(String(100), default=None)
    transport_type: Mapped[str | None] = mapped_column(String(100), default=None)
    latitude: Mapped[Float | None] = mapped_column(Float, default=None)
    longitude: Mapped[Float | None] = mapped_column(Float, default=None)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"))
    region: Mapped["Region"] = relationship("Region", back_populates="points")
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="points")


class Region(Base, StationCommonMixin):
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="regions")
    points: Mapped[list["Point"]] = relationship("Point", back_populates="region")


class Country(Base, StationCommonMixin):
    regions: Mapped[list["Region"]] = relationship("Region", back_populates="country")
    points: Mapped[list["Point"]] = relationship("Point", back_populates="country")


class UpdateDate(Base):
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def create_db_schema():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except SQLAlchemyError as e:
        raise exc.CreateSchemaError(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(create_db_schema)
