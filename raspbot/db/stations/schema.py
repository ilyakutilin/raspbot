from typing import cast

from sqlalchemy import Float as Float_org
from sqlalchemy import ForeignKey, Integer, String, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql.type_api import TypeEngine

from raspbot.config import exceptions as exc


# declarative base class
class Base(DeclarativeBase):
    pass


# sqlalchemy.Float is treated as decimal.Decimal, not float.
# So this is a workaround to stop mypy from complaining.
# https://github.com/dropbox/sqlalchemy-stubs/issues/178
Float = cast(type[TypeEngine[float]], Float_org)
engine = create_engine("sqlite:///stations.db", echo=True)


class Station(Base):
    __tablename__ = "stations"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), default="")
    station_type: Mapped[str] = mapped_column(String(100), default="")
    transport_type: Mapped[str] = mapped_column(String(100), default="")
    latitude: Mapped[Float | None] = mapped_column(Float, default=None)
    longitude: Mapped[Float | None] = mapped_column(Float, default=None)
    yandex_code: Mapped[str] = mapped_column(String(100), default="")
    settlement_id: Mapped[int] = mapped_column(Integer, ForeignKey("settlements.id"))
    settlement: Mapped["Settlement"] = relationship(
        "Settlement", back_populates="stations"
    )
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    region: Mapped["Region"] = relationship("Region", back_populates="stations")
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="stations")


class Settlement(Base):
    __tablename__ = "settlements"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), default="")
    yandex_code: Mapped[str | None] = mapped_column(String(100), default=None)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    region: Mapped["Region"] = relationship("Region", back_populates="settlements")
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="settlements")
    stations: Mapped[list["Station"]] = relationship(
        "Station", back_populates="settlement"
    )


class Region(Base):
    __tablename__ = "regions"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), default="")
    yandex_code: Mapped[str | None] = mapped_column(String(100), default=None)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship("Country", back_populates="regions")
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement", back_populates="region"
    )
    stations: Mapped[list["Station"]] = relationship("Station", back_populates="region")


class Country(Base):
    __tablename__ = "countries"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), default="")
    yandex_code: Mapped[str | None] = mapped_column(String(100), default=None)
    regions: Mapped[list["Region"]] = relationship("Region", back_populates="country")
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement", back_populates="country"
    )
    stations: Mapped[list["Station"]] = relationship(
        "Station", back_populates="country"
    )


def create_db_schema():
    try:
        Base.metadata.create_all(engine)
    except SQLAlchemyError as e:
        raise exc.CreateSchemaError(f"{type(e).__name__}: {e}")


if __name__ == "main":
    create_db_schema()
