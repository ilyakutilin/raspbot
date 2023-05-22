"""
Explanation of the 'Yandex object'.

For the purposes of this module, a 'Yandex object' means a dictionary
containing the data on a country / region / settlement / station.
I.e. it is not a Python object per se, it's just an abstraction to describe
a unit of the Yandex station data structure.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.base import AsyncSessionLocal
from raspbot.db.stations import models, schema
from raspbot.db.stations.parse import structure_initial_data
from raspbot.settings import BASE_DIR

logger = configure_logging(__name__)

INITIAL_DATA = BASE_DIR / "sample.json"


def _log_object_creation(obj: object) -> None:
    """Logs object creation and raises exceptions."""
    if obj:
        logger.debug(f"SUCCESS: {obj} has been created.")
    else:
        raise exc.SQLObjectError(f"FAILURE: object {obj} has NOT been created.")


async def _get_regions(world: schema.World) -> list[schema.RegionsByCountry]:
    """Receives the list of countries and returns the regions by countries."""
    regions_by_country = []
    async with AsyncSessionLocal() as session:
        for country in world.countries:
            sql_obj = models.Country(
                title=country.title,
                yandex_code=country.codes.yandex_code,
            )
            _log_object_creation(sql_obj)
            session.add(sql_obj)
            regions = schema.RegionsByCountry(
                country=sql_obj,
                regions=country.regions,
            )
            _log_object_creation(regions)
            regions_by_country.append(regions)
        await session.commit()
    return regions_by_country


async def _get_settlements(
    regions_by_country: Iterable[schema.RegionsByCountry],
) -> list[schema.SettlementsByRegion]:
    """Receives the list of regions and returns the settlements by regions."""
    settlements_by_region = []
    async with AsyncSessionLocal() as session:
        for item in regions_by_country:
            for region in item.regions:
                sql_obj = models.Region(
                    title=region.title,
                    yandex_code=region.codes.yandex_code,
                    country=item.country,
                )
                _log_object_creation(sql_obj)
                session.add(sql_obj)
                settlements = schema.SettlementsByRegion(
                    region=sql_obj,
                    settlements=region.settlements,
                )
                _log_object_creation(settlements)
                settlements_by_region.append(settlements)
        await session.commit()
    return settlements_by_region


async def _get_stations(
    settlements_by_region: Iterable[schema.SettlementsByRegion],
) -> list[schema.StationsBySettlement]:
    """Receives the settlements and returns the stations by settlements."""
    stations_by_settlement = []
    async with AsyncSessionLocal() as session:
        for item in settlements_by_region:
            for settlement in item.settlements:
                sql_obj = models.Settlement(
                    title=settlement.title,
                    yandex_code=settlement.codes.yandex_code,
                    region=item.region,
                    country=item.region.country,
                )
                _log_object_creation(sql_obj)
                session.add(sql_obj)
                stations = schema.StationsBySettlement(
                    settlement=sql_obj,
                    stations=settlement.stations,
                )
                _log_object_creation(stations)
                stations_by_settlement.append(stations)
        await session.commit()
    return stations_by_settlement


async def _add_stations_to_db(
    stations_by_settlement: Iterable[schema.StationsBySettlement],
) -> None:
    """Receives the list of stations and adds them to the database."""
    async with AsyncSessionLocal() as session:
        for item in stations_by_settlement:
            for station in item.stations:
                sql_obj = models.Station(
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
        await session.commit()


async def populate_db(initial_data: Mapping | Path) -> None:
    try:
        world = structure_initial_data(initial_data)
    except exc.DataStructureError as e:
        logger.exception(f"Initial data structuring failed: {e}", exc_info=True)
        return
    else:
        if world is None:
            return
        logger.debug("Initial data structured.")

    try:
        await models.create_db_schema()
    except exc.SQLError as e:
        logger.exception(f"Creating Initial data DB schema failed: {e}", exc_info=True)
        return
    else:
        logger.debug("DB Schema created.")

    try:
        regions = await _get_regions(world)
        settlements = await _get_settlements(regions)
        stations = await _get_stations(settlements)
        await _add_stations_to_db(stations)
    except exc.SQLError as e:
        logger.exception(f"Adding stations to DB failed: {e}", exc_info=True)
    else:
        logger.debug("Stations added to DB.")
    logger.debug("DB is now populated.")


if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(populate_db(INITIAL_DATA))
    finish_time = datetime.now()
    logger.info(f"It took {(finish_time - start_time).total_seconds()} seconds.")
