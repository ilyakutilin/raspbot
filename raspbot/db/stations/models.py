import asyncio
from datetime import datetime
from typing import cast

from sqlalchemy import Boolean, CheckConstraint, DateTime
from sqlalchemy import Float as Float_org
from sqlalchemy import ForeignKey, Integer, String, case
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.type_api import TypeEngine

from raspbot.core import exceptions as exc
from raspbot.db.base import Base, engine
from raspbot.db.users.models import Route

# sqlalchemy.Float is treated as decimal.Decimal, not float.
# So this is a workaround to stop mypy from complaining.
# https://github.com/dropbox/sqlalchemy-stubs/issues/178
Float = cast(type[TypeEngine[float]], Float_org)


class StationCommonMixin(object):
    title: Mapped[str] = mapped_column(String(100), default="")
    yandex_code: Mapped[str | None] = mapped_column(String(100), default=None)

    def __repr__(self):
        return f"{self.__class__.__name__} {self.title}"


class Station(Base, StationCommonMixin):
    station_type: Mapped[str] = mapped_column(String(100), default="")
    transport_type: Mapped[str] = mapped_column(String(100), default="")
    latitude: Mapped[Float | None] = mapped_column(Float, default=None)
    longitude: Mapped[Float | None] = mapped_column(Float, default=None)
    yandex_code: Mapped[str] = mapped_column(String(100), default="")
    point_id: Mapped[int] = mapped_column(ForeignKey("point.id"))
    point: Mapped["Point"] = relationship("Point", back_populates="station")
    settlement_id: Mapped[int] = mapped_column(Integer, ForeignKey("settlement.id"))
    settlement: Mapped["Settlement"] = relationship(
        "Settlement", back_populates="stations"
    )
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"))
    region: Mapped["Region"] = relationship("Region", back_populates="stations")
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="stations")


class Settlement(Base, StationCommonMixin):
    point_id: Mapped[int] = mapped_column(ForeignKey("point.id"))
    point: Mapped["Point"] = relationship("Point", back_populates="settlement")
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"))
    region: Mapped["Region"] = relationship("Region", back_populates="settlements")
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="settlements")
    stations: Mapped[list["Station"]] = relationship(
        "Station", back_populates="settlement"
    )


class Point(Base):
    station_id: Mapped[int] = mapped_column(ForeignKey("station.id"))
    station: Mapped["Station"] = relationship("Station", back_populates="point")
    settlement_id: Mapped[int] = mapped_column(ForeignKey("settlement.id"))
    station: Mapped["Settlement"] = relationship("Settlement", back_populates="point")
    is_station: Mapped[bool] = mapped_column(Boolean, default=True)
    is_station = column_property(
        case([(station_id.isnot(None) & settlement_id.is_(None), True)], else_=False)
    )
    routes: Mapped[list["Route"]] = relationship("Route", back_populates="point")
    __table_args__ = (
        CheckConstraint(
            case(
                [
                    (station_id.isnot(None), settlement_id.is_(None)),
                    (station_id.is_(None), settlement_id.isnot(None)),
                ],
                else_=False,
            ),
            name="point_constraint",
        ),
        CheckConstraint(
            station_id.isnot(None) | settlement_id.isnot(None),
            name="at_least_one_field_required",
        ),
    )


class Region(Base, StationCommonMixin):
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="regions")
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement", back_populates="region"
    )
    stations: Mapped[list["Station"]] = relationship("Station", back_populates="region")


class Country(Base, StationCommonMixin):
    regions: Mapped[list["Region"]] = relationship("Region", back_populates="country")
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement", back_populates="country"
    )
    stations: Mapped[list["Station"]] = relationship(
        "Station", back_populates="country"
    )


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
