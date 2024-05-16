"""
Explanation of the 'Yandex object'.

For the purposes of this module, a 'Yandex object' means a dictionary
containing the data on a country / region / settlement / station.
I.e. it is not a Python object per se, it's just an abstraction to describe
a unit of the Yandex station data structure.
"""

import asyncio
import json
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any, AsyncGenerator, Type

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import DeclarativeMeta

from raspbot.apicalls.base import get_response
from raspbot.apicalls.search import TransportTypes
from raspbot.bot.send_msg import send_telegram_message_to_admin
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging, log
from raspbot.db.base import async_session_factory
from raspbot.db.stations import models, schema
from raspbot.db.stations.schema import RegionPD
from raspbot.settings import settings

logger = configure_logging(__name__)


@log(logger)
def _log_object_creation(obj: object) -> None:
    """Logs object creation and raises exceptions."""
    if obj:
        logger.debug(f"SUCCESS: {obj} has been created.")

    else:
        raise exc.SQLObjectError(f"FAILURE: object {obj} has NOT been created.")


@log(logger)
async def _instance_exists_in_database(
    session: AsyncSession, model: Type[DeclarativeMeta], **kwargs
) -> Type[DeclarativeMeta] | None:
    # Construct the filter criteria dynamically using kwargs
    filters = [getattr(model, key) == value for key, value in kwargs.items()]

    # Query the database for an instance with the specified attribute values
    query = await session.execute(select(model).where(*filters))
    existing_instance = query.first()

    return existing_instance


@log(logger)
def _get_initial_data_dict(initial_data: Path | Any) -> dict | None:
    """Returns the initial data as a dictionary."""
    if isinstance(initial_data, Path):
        with open(file=initial_data, mode="r", encoding="UTF-8") as file:
            json_data = json.load(file)
            return json_data

    return None


@log(logger)
async def _yield_regions_pd(
    initial_data: dict | Path | Any,
) -> AsyncGenerator[RegionPD, None]:
    """Structures the initial data."""
    initial_data_dict = (
        _get_initial_data_dict(initial_data)
        if not isinstance(initial_data, dict)
        else initial_data
    )
    if not initial_data_dict:
        raise exc.DataStructureError("There is no initial data.")
    countries = initial_data_dict.get("countries")
    if not countries:
        raise exc.DataStructureError("There is no 'countries' key in the initial data.")
    for c in countries:
        regions = c.get("regions")
        if c.get("title") == "Россия" and isinstance(regions, list):
            for r in regions:
                try:
                    region_pd = RegionPD.model_validate(obj=r)
                except ValidationError as e:
                    region_title = r.get("title") or "Unknown Region"
                    raise exc.DataStructureError(
                        f"Pydantic data validation for region {region_title} failed: "
                        f"{e}."
                    )
                if region_pd.title:
                    yield region_pd


@log(logger)
async def _yield_regions_orm_and_add_to_db(
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
        try:
            _log_object_creation(sql_obj)
        except exc.SQLObjectError as e:
            logger.error(e)
            continue
        session.add(sql_obj)
        await session.flush()
        yield tuple((sql_obj.id, region))


@log(logger)
async def _yield_points_by_region_pd(
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
        try:
            _log_object_creation(points)
        except exc.SQLObjectError as e:
            logger.error(e)
            continue
        yield points


@log(logger)
async def _add_points_to_db(  # noqa: C901
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
            try:
                _log_object_creation(sql_obj)
            except exc.SQLObjectError as e:
                logger.error(e)
                continue
            session.add(sql_obj)

        for station in item.stations:
            if not station.codes.yandex_code:
                logger.warning(
                    f"FAILURE: station {station.title} has NOT been created: "
                    "no yandex_code"
                )
                continue
            if station.transport_type not in (
                TransportTypes.TRAIN.value,
                TransportTypes.SUBURBAN.value,
                "",
                None,
            ):
                logger.info(
                    f"Skipping non-train transport type: {station.transport_type} "
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
            try:
                _log_object_creation(sql_obj)
            except exc.SQLObjectError as e:
                logger.error(e)
                continue
            session.add(sql_obj)
    await session.flush()


@log(logger)
async def _add_last_updated_time(session: AsyncSession) -> None:
    """Adds the date and time when the stations DB was last updated."""
    sql_obj = models.LastUpdatedORM()
    session.add(sql_obj)


@log(logger)
async def populate_db(initial_data: dict | Path) -> None:
    """Populates the stations DB with the initial data."""
    logger.debug("Ready for the DB population.")

    try:
        regions_generator = _yield_regions_pd(initial_data)
    except exc.DataStructureError as e:
        logger.exception(f"Data structure error: {e}", exc_info=True)

    async with async_session_factory() as session:
        try:
            regions_orm_generator = _yield_regions_orm_and_add_to_db(
                regions_generator, session
            )
            points_by_region_generator = _yield_points_by_region_pd(
                regions_orm_generator, session
            )
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

        logger.info("DB is now populated.")


async def main() -> None:
    """Obtains the initial data and populates the stations DB with it."""
    initial_data: dict = await get_response(
        endpoint=settings.STATIONS_LIST_ENDPOINT, headers=settings.headers
    )

    logger.info("Starting to populate the Stations DB.")
    await populate_db(initial_data)


if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    finish_time = datetime.now()
    it_took = (
        f"It took {(finish_time - start_time).total_seconds()} seconds "
        "to fill the Stations DB with the data from Yandex."
    )
    logger.info(it_took)
    asyncio.run(
        send_telegram_message_to_admin(
            message=(f"Station DB has been populated. {it_took}")
        )
    )
