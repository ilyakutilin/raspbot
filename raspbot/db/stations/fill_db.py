"""
Explanation of the 'Yandex object'.

For the purposes of this module, a 'Yandex object' means a dictionary
containing the data on a country / region / settlement / station.
I.e. it is not a Python object per se, it's just an abstraction to describe
a unit of the Yandex station data structure.
"""

import asyncio
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Iterable

from raspbot.apicalls.base import get_response
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.base import AsyncSessionLocal
from raspbot.db.stations import models, schema
from raspbot.db.stations.parse import structure_initial_data
from raspbot.settings import settings

logger = configure_logging(__name__)


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


async def _get_points(
    regions_by_country: Iterable[schema.RegionsByCountry],
) -> list[schema.PointsByRegion]:
    """Receives the list of regions and returns the settlements by regions."""
    points_by_region = []
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
                stations = list(
                    chain.from_iterable(
                        [settlement.stations for settlement in region.settlements]
                    )
                )
                points = schema.PointsByRegion(
                    region=sql_obj, settlements=region.settlements, stations=stations
                )
                _log_object_creation(points)
                points_by_region.append(points)
        await session.commit()
    return points_by_region


async def _add_points_to_db(
    points_by_region: Iterable[schema.PointsByRegion],
) -> None:
    """Receives the list of stations and adds them to the database."""
    async with AsyncSessionLocal() as session:
        for item in points_by_region:
            for settlement in item.settlements:
                if not settlement.codes.yandex_code:
                    logger.warning(
                        f"FAILURE: settlement {settlement.title} has NOT been created: "
                        "no yandex_code"
                    )
                    continue
                sql_obj = models.Point(
                    point_type=models.PointTypeEnum.settlement,
                    title=settlement.title,
                    yandex_code=settlement.codes.yandex_code,
                    region=item.region,
                    country=item.region.country,
                )
                _log_object_creation(sql_obj)
                session.add(sql_obj)

            for station in item.stations:
                if not station.codes.yandex_code:
                    logger.warning(
                        f"FAILURE: station {station.title} has NOT been created: "
                        "no yandex_code"
                    )
                    continue
                latitude = (
                    station.latitude if isinstance(station.latitude, float) else None
                )
                longitude = (
                    station.longitude if isinstance(station.longitude, float) else None
                )
                sql_obj = models.Point(
                    point_type=models.PointTypeEnum.station,
                    title=station.title,
                    yandex_code=station.codes.yandex_code,
                    station_type=station.station_type,
                    transport_type=station.transport_type,
                    latitude=latitude,
                    longitude=longitude,
                    region=item.region,
                    country=item.region.country,
                )
                _log_object_creation(sql_obj)
                session.add(sql_obj)

        await session.commit()


async def _add_updated_date() -> None:
    """Adds the date and time when the stations DB was last updated."""
    async with AsyncSessionLocal() as session:
        sql_obj = models.UpdateDate()
        session.add(sql_obj)
        await session.commit()


async def populate_db(initial_data: dict | Path) -> None:
    try:
        world = structure_initial_data(initial_data)
    except exc.DataStructureError as e:
        logger.exception(f"Initial data structuring failed: {e}", exc_info=True)
        return
    else:
        if world is None:
            return
        logger.debug("Ready for the DB population.")

    try:
        regions = await _get_regions(world)
        points = await _get_points(regions)
        await _add_points_to_db(points)
    except exc.SQLError as e:
        logger.exception(f"Adding stations to DB failed: {e}", exc_info=True)
    else:
        logger.debug("Stations added to DB.")
    logger.debug("DB is now populated.")

    try:
        await _add_updated_date()
    except exc.SQLError as e:
        logger.exception(f"Adding the updated date to DB failed: {e}", exc_info=True)


async def main() -> None:
    initial_data: dict = await get_response(
        endpoint=settings.STATIONS_LIST_ENDPOINT, headers=settings.headers
    )
    logger.debug("Starting to populate the Stations DB.")
    await populate_db(initial_data)


if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    finish_time = datetime.now()
    logger.info(
        f"It took {(finish_time - start_time).total_seconds()} seconds "
        "to fill the Stations DB with the data from Yandex."
    )
