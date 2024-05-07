import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TEST

from raspbot.bot import routes_router, start_router, timetable_router, users_router
from raspbot.core.logging import configure_logging
from raspbot.settings import settings

logger = configure_logging(name=__name__)


custom_session = AiohttpSession(api=TEST)


def get_bot(test: bool = False) -> Bot:
    """Returns the bot."""
    main_bot = Bot(token=settings.TELEGRAM_TOKEN)
    test_bot = Bot(token=settings.TELEGRAM_TESTENV_TOKEN, session=custom_session)
    bot = test_bot if test else main_bot
    return bot


async def start_bot(bot: Bot, handle_signals: bool = True):
    """Starts the bot."""
    dp = Dispatcher()
    dp.include_routers(users_router, start_router, routes_router, timetable_router)

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info(
        "Starting the {} bot.".format("test" if bot.session.api == TEST else "")
    )
    await dp.start_polling(bot, handle_signals=handle_signals)

    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(start_bot(test=True))
