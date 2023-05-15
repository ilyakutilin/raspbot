from typing import cast

from sqlalchemy import Column
from sqlalchemy import Float as Float_org
from sqlalchemy import ForeignKey, Integer, String, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.type_api import TypeEngine

from raspbot.config import exceptions as exc

Base = declarative_base()
# sqlalchemy.Float is treated as decimal.Decimal, not float.
# So this is a workaround to stop mypy from complaining.
# https://github.com/dropbox/sqlalchemy-stubs/issues/178
Float = cast(type[TypeEngine[float]], Float_org)
engine = create_engine("sqlite:///stations.db")


class Station(Base):
    __tablename__ = "stations"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False, default="")
    station_type = Column(String(100), nullable=False, default="")
    transport_type = Column(String(100), nullable=False, default="")
    latitude = Column(Float, nullable=True, default=None)
    longitude = Column(Float, nullable=True, default=None)
    yandex_code = Column(String(100), nullable=False, default="")
    settlement_id = Column(Integer, ForeignKey("settlements.id"))
    settlement = relationship("Settlement", back_populates="stations")
    region_id = Column(Integer, ForeignKey("regions.id"))
    region = relationship("Region", back_populates="stations")
    country_id = Column(Integer, ForeignKey("countries.id"))
    country = relationship("Country", back_populates="stations")


class Settlement(Base):
    __tablename__ = "settlements"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False, default="")
    yandex_code = Column(String(100), nullable=True, default=None)
    region_id = Column(Integer, ForeignKey("regions.id"))
    region = relationship("Region", back_populates="settlements")
    country_id = Column(Integer, ForeignKey("countries.id"))
    country = relationship("Country", back_populates="settlements")
    stations = relationship("Station", back_populates="settlement")


class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False, default="")
    yandex_code = Column(String(100), nullable=True, default=None)
    country_id = Column(Integer, ForeignKey("countries.id"))
    country = relationship("Country", back_populates="regions")
    settlements = relationship("Settlement", back_populates="region")
    stations = relationship("Station", back_populates="region")


class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False, default="")
    yandex_code = Column(String(100), nullable=True, default=None)
    regions = relationship("Region", back_populates="country")
    settlements = relationship("Settlement", back_populates="country")
    stations = relationship("Station", back_populates="country")


def create_db_schema():
    try:
        Base.metadata.create_all(engine)
    except SQLAlchemyError as e:
        raise exc.CreateSchemaError(f"{type(e).__name__}: {e}")


if __name__ == "main":
    create_db_schema()
