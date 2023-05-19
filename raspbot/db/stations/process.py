"""
Explanation of the 'Yandex object'.

For the purposes of this module, a 'Yandex object' means a dictionary
containing the data on a country / region / settlement / station.
I.e. it is not a Python object per se, it's just an abstraction to describe
a unit of the Yandex station data structure.
"""

from pathlib import Path
from typing import Iterable, Mapping, NamedTuple

from sqlalchemy.orm import Session

from raspbot.config import exceptions as exc
from raspbot.config.logging import configure_logging
from raspbot.settings import settings

from . import getdata as pd
from . import schema as sql

session = Session(bind=sql.engine)

logger = configure_logging(__name__)

INITIAL_DATA = settings.BASE_DIR / "sample.json"


class RegionsByCountry(NamedTuple):
    country: sql.Country
    regions: list[pd.Region]

    def __repr__(self) -> str:
        return self.country.title


class SettlementsByRegion(NamedTuple):
    region: sql.Region
    settlements: list[pd.Settlement]

    def __repr__(self) -> str:
        return self.region.title


class StationsBySettlement(NamedTuple):
    settlement: sql.Settlement
    stations: list[pd.Station]

    def __repr__(self) -> str:
        return self.settlement.title


def _log_object_creation(obj: Any) -> None:
    """Logs object creation and raises exceptions."""
    if obj:
        logger.debug(f"SUCCESS: {obj.__class__.__name__} {obj} has been created.")
    else:
        raise exc.SQLObjectError(
            f"FAILURE: object {obj.__class__.__name__} {obj} has NOT been created."
        )


def _get_regions(world: pd.World) -> list[RegionsByCountry]:
    """Receives the list of countries and returns the regions by countries."""
    regions_by_country = []
    for country in world.countries:
        sql_obj = sql.Country(
            title=country.title,
            yandex_code=country.codes.yandex_code,
        )
        _log_object_creation(sql_obj)
        session.add(sql_obj)
        regions = RegionsByCountry(
            country=sql_obj,
            regions=country.regions,
        )
        _log_object_creation(regions)
        regions_by_country.append(regions)
    session.commit()
    return regions_by_country


def _get_settlements(
    regions_by_country: Iterable[RegionsByCountry],
) -> list[SettlementsByRegion]:
    """Receives the list of regions and returns the settlements by regions."""
    settlements_by_region = []
    for item in regions_by_country:
        for region in item.regions:
            sql_obj = sql.Region(
                title=region.title,
                yandex_code=region.codes.yandex_code,
                country=item.country,
            )
            _log_object_creation(sql_obj)
            session.add(sql_obj)
            settlements = SettlementsByRegion(
                region=sql_obj,
                settlements=region.settlements,
            )
            _log_object_creation(settlements)
            settlements_by_region.append(settlements)
    session.commit()
    return settlements_by_region


def _get_stations(
    settlements_by_region: Iterable[SettlementsByRegion],
) -> list[StationsBySettlement]:
    """Receives the settlements and returns the stations by settlements."""
    stations_by_settlement = []
    for item in settlements_by_region:
        for settlement in item.settlements:
            sql_obj = sql.Settlement(
                title=settlement.title,
                yandex_code=settlement.codes.yandex_code,
                region=item.region,
                country=item.region.country,
            )
            _log_object_creation(sql_obj)
            session.add(sql_obj)
            stations = StationsBySettlement(
                settlement=sql_obj,
                stations=settlement.stations,
            )
            _log_object_creation(stations)
            stations_by_settlement.append(stations)
    session.commit()
    return stations_by_settlement


def _add_stations_to_db(
    stations_by_settlement: Iterable[StationsBySettlement],
) -> None:
    """Receives the list of stations and adds them to the database."""
    for item in stations_by_settlement:
        for station in item.stations:
            sql_obj = sql.Station(
                title=station.title,
                yandex_code=station.codes.yandex_code
                if station.codes.yandex_code is not None
                else "",
                station_type=station.station_type,
                transport_type=station.transport_type,
                latitude=station.latitude
                if isinstance(station.latitude, float)
                else None,
                longitude=station.longitude
                if isinstance(station.longitude, float)
                else None,
                settlement=item.settlement,
                region=item.settlement.region,
                country=item.settlement.country,
            )
            _log_object_creation(sql_obj)
            session.add(sql_obj)
    session.commit()


def populate_db(initial_data: Mapping | Path) -> None:
    try:
        world = pd.structure_initial_data(initial_data)
    except exc.DataStructureError as e:
        logger.exception(f"Initial data structuring failed: {e}", exc_info=True)
        return
    else:
        if world is None:
            return
        logger.debug("Initial data structured.")

    try:
        sql.create_db_schema()
    except exc.SQLError as e:
        logger.exception(f"Creating Initial data DB schema failed: {e}", exc_info=True)
        return
    else:
        logger.debug("DB Schema created.")

    try:
        regions = _get_regions(world)
        settlements = _get_settlements(regions)
        stations = _get_stations(settlements)
        _add_stations_to_db(stations)
    except exc.SQLError as e:
        logger.exception(f"Adding stations to DB failed: {e}", exc_info=True)
    else:
        logger.debug("Stations added to DB.")
    logger.debug("DB is now populated.")


if __name__ == "main":
    populate_db(INITIAL_DATA)
