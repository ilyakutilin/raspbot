import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler, BaseScheduler
from sqlalchemy import func, select

from raspbot.core.logging import configure_logging
from raspbot.db.base import async_session_factory
from raspbot.db.stations.models import LastUpdatedORM
from raspbot.db.stations.parse import main
from raspbot.settings import settings

logger = configure_logging(__name__)


async def check_last_station_db_update(
    days_between_updates: int = settings.DAYS_BETWEEN_STATIONS_DB_UPDATE,
) -> None:
    """Checks when the stations DB was last updated."""
    logger.info("Starting to check when the stations DB was last updated.")
    async with async_session_factory() as session:
        query = await session.execute(select(func.max(LastUpdatedORM.created_at)))
        last_updated = query.scalar()
        if not last_updated:
            logger.info(
                "There is no information in the DB about the stations DB update date."
                "Therefore, starting DB population process now."
            )
            await main()
        else:
            max_time_diff = timedelta(days=days_between_updates)
            current_time_diff = datetime.now(tz=timezone.utc) - last_updated
            if current_time_diff > max_time_diff:
                logger.info(
                    f"It was more than {days_between_updates} days since the "
                    "stations DB was last updated. Therefore, starting DB population "
                    "process now."
                )
                await main()
            logger.info(
                "The stations DB was last updated at "
                f"{last_updated.strftime(settings.LOG_DT_FMT)}. Less than "
                f"{days_between_updates} days since the last update. No action needed."
            )


def get_scheduler() -> BaseScheduler:
    """Returns the scheduler."""
    return AsyncIOScheduler()


async def start_update_monitoring(scheduler: AsyncIOScheduler) -> None:
    """Starts the update monitoring."""
    scheduler.add_job(check_last_station_db_update, "cron", hour=3)
    logger.info("Starting the stations DB update date monitoring.")
    scheduler.start()
    while True:
        await asyncio.sleep(1800)
