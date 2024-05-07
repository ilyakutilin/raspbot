import argparse
import asyncio
import os
import sys

current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from aiogram.exceptions import TelegramRetryAfter  # noqa

from raspbot.bot.bot import get_bot, start_bot  # noqa
from raspbot.core.logging import configure_logging  # noqa
from raspbot.db.stations.schedule import (  # noqa
    check_last_station_db_update,
    get_scheduler,
    start_update_monitoring,
)

logger = configure_logging(__name__)


def get_args() -> argparse.Namespace:
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description="Telegram Raspbot")
    parser.add_argument(
        "-t", "--test", action="store_true", help="Run in test environment"
    )
    parser.add_argument(
        "-n", "--nomonitor", action="store_true", help="Without update monitoring"
    )
    return parser.parse_args()


async def main() -> None:
    """Entrypoint starting all the things."""
    args = get_args()
    bot = get_bot(test=args.test)
    if args.nomonitor:
        await start_bot(bot)
    else:
        await check_last_station_db_update()
        scheduler = get_scheduler()
        bot_task = asyncio.ensure_future(start_bot(bot=bot, handle_signals=False))
        scheduler_task = asyncio.ensure_future(start_update_monitoring(scheduler))
        try:
            await asyncio.gather(bot_task, scheduler_task)
        except asyncio.exceptions.CancelledError:
            logger.info("Shutting down the update monitoring scheduler...")
            scheduler.shutdown()
            logger.info("Update monitoring scheduler has been shut down.")

            try:
                logger.info("Stopping the bot...")
                await bot.close()
                logger.info("Bot has been stopped.")
            except TelegramRetryAfter:
                logger.error("An attempt to stop the bot hit TelegramRetryAfter.")
            finally:
                await bot.session.close()
                logger.info("Client session has been terminated.")


if __name__ == "__main__":
    asyncio.run(main())
