"""
Explanation of the 'Yandex object'.

For the purposes of this module, a 'Yandex object' means a dictionary
containing the data on a country / region / settlement / station.
I.e. it is not a Python object per se, it's just an abstraction to describe
a unit of the Yandex station data structure.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from itertools import chain
from pathlib import Path
from typing import AsyncGenerator, Type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import DeclarativeMeta

from raspbot.apicalls.base import get_response
from raspbot.apicalls.search import TransportTypes
from raspbot.bot.send_msg import send_telegram_message_to_admin
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.base import async_session_factory
from raspbot.db.stations import models, schema
from raspbot.db.stations.parse import yield_regions
from raspbot.settings import settings

logger = configure_logging(__name__)


def _log_object_creation(obj: object) -> None:
    """Logs object creation and raises exceptions."""
    if obj:
        logger.debug(f"SUCCESS: {obj} has been created.")

    else:
        raise exc.SQLObjectError(f"FAILURE: object {obj} has NOT been created.")


async def _instance_exists_in_database(
    session: AsyncSession, model: Type[DeclarativeMeta], **kwargs
) -> Type[DeclarativeMeta] | None:
    # Construct the filter criteria dynamically using kwargs
    filters = [getattr(model, key) == value for key, value in kwargs.items()]

    # Query the database for an instance with the specified attribute values
    query = await session.execute(select(model).where(*filters))
    existing_instance = query.first()

    return existing_instance


async def _create_regions_orm_and_yield(
    region_generator: AsyncGenerator[schema.RegionPD, None], session: AsyncSession
) -> AsyncGenerator[tuple[int, schema.RegionPD], None]:
    """A generator that receives the regions and gets their DB IDs.

    It yields tuples containing a region ORM object ID and a corresponding pydantic
    schema model instance. Adds regions to the session as it goes.
    """
    async for region in region_generator:
        attrs = {
            "title": region.title,
            "yandex_code": region.codes.yandex_code,
        }
        existing_region = await _instance_exists_in_database(
            session, models.RegionORM, **attrs
        )
        if existing_region:
            continue
        sql_obj = models.RegionORM(**attrs)
        _log_object_creation(sql_obj)
        session.add(sql_obj)
        await session.flush()
        yield tuple((sql_obj.id, region))


async def _get_points(
    regions_orm_generator: AsyncGenerator[tuple[int, schema.RegionPD], None],
    session: AsyncSession,
) -> AsyncGenerator[schema.PointsByRegionPD, None]:
    """Receives regions and returns settlements by regions."""
    async for region in regions_orm_generator:
        region_sql_obj = await session.get(models.RegionORM, region[0])
        region_pd_obj = region[1]
        stations = list(
            chain.from_iterable(
                [settlement.stations for settlement in region_pd_obj.settlements]
            )
        )
        points = schema.PointsByRegionPD(
            region_orm=region_sql_obj,
            settlements=region_pd_obj.settlements,
            stations=stations,
        )
        _log_object_creation(points)
        yield points


async def _add_points_to_db(
    points_by_region_generator: AsyncGenerator[schema.PointsByRegionPD, None],
    session: AsyncSession,
) -> None:
    """Receives stations and adds them to the database."""
    async for item in points_by_region_generator:
        for settlement in item.settlements:
            if not settlement.codes.yandex_code:
                logger.warning(
                    f"FAILURE: settlement {settlement.title} has NOT been created: "
                    "no yandex_code"
                )
                continue
            attrs = {
                "point_type": models.PointTypeEnum.settlement,
                "title": settlement.title,
                "yandex_code": settlement.codes.yandex_code,
            }
            existing_settlement = await _instance_exists_in_database(
                session, models.PointORM, **attrs
            )
            if existing_settlement:
                continue
            sql_obj = models.PointORM(region=item.region_orm, **attrs)
            _log_object_creation(sql_obj)
            session.add(sql_obj)

        for station in item.stations:
            if not station.codes.yandex_code:
                logger.warning(
                    f"FAILURE: station {station.title} has NOT been created: "
                    "no yandex_code"
                )
                continue
            if station.transport_type != TransportTypes.SUBURBAN.value:
                logger.info(
                    f"Skipping non-suburban transport type: {station.transport_type} "
                    f"for station {station.title}"
                )
                continue
            attrs = {
                "point_type": models.PointTypeEnum.station,
                "title": station.title,
                "yandex_code": station.codes.yandex_code,
            }
            existing_station = await _instance_exists_in_database(
                session, models.PointORM, **attrs
            )
            if existing_station:
                continue
            latitude = station.latitude if isinstance(station.latitude, float) else None
            longitude = (
                station.longitude if isinstance(station.longitude, float) else None
            )
            sql_obj = models.PointORM(
                station_type=station.station_type,
                latitude=latitude,
                longitude=longitude,
                region=item.region_orm,
                **attrs,
            )
            _log_object_creation(sql_obj)
            session.add(sql_obj)
    await session.flush()


async def _add_last_updated_time(session: AsyncSession) -> None:
    """Adds the date and time when the stations DB was last updated."""
    sql_obj = models.LastUpdatedORM()
    session.add(sql_obj)


async def populate_db(initial_data: dict | Path) -> None:
    """Populates the stations DB with the initial data."""
    logger.debug("Ready for the DB population.")

    try:
        regions_generator = yield_regions(initial_data)
    except exc.DataStructureError as e:
        logger.exception(f"Data structure error: {e}", exc_info=True)

    async with async_session_factory() as session:
        try:
            regions_orm_generator = _create_regions_orm_and_yield(
                regions_generator, session
            )
            points_by_region_generator = _get_points(regions_orm_generator, session)
            await _add_points_to_db(points_by_region_generator, session)
        except exc.SQLError as e:
            logger.exception(f"Adding stations to DB failed: {e}", exc_info=True)
        else:
            logger.debug("Stations added to DB.")

        try:
            await _add_last_updated_time(session)
        except exc.SQLError as e:
            logger.exception(
                f"Adding the updated date to DB failed: {e}", exc_info=True
            )

        try:
            await session.commit()
        except Exception as e:
            logger.exception(f"DB population failed: {e}", exc_info=True)
            await send_telegram_message_to_admin(
                message=f"Station DB population failed: {e}"
            )

        logger.debug("DB is now populated.")
        await send_telegram_message_to_admin(message="Station DB is now populated.")


async def main() -> None:
    """Obtains the initial data and populates the stations DB with it."""
    initial_data: dict = await get_response(
        endpoint=settings.STATIONS_LIST_ENDPOINT, headers=settings.headers
    )

    logger.debug("Starting to populate the Stations DB.")
    await populate_db(initial_data)


async def check_last_station_db_update() -> None:
    """Checks when the stations DB was last updated."""
    async with async_session_factory() as session:
        query = await session.execute(select(func.max(models.LastUpdatedORM.updated)))
        last_updated = query.scalar()
        if not last_updated:
            await main()
        max_time_diff = timedelta(days=14)
        current_time_diff = datetime.now(tz=timezone.utc) - last_updated
        if current_time_diff > max_time_diff:
            await main()


if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    finish_time = datetime.now()
    logger.info(
        f"It took {(finish_time - start_time).total_seconds()} seconds "
        "to fill the Stations DB with the data from Yandex."
    )
