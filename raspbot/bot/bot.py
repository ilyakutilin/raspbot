import asyncio

from aiogram import Bot, Dispatcher

from raspbot.bot import routes_router, start_router, timetable_router, users_router
from raspbot.core.logging import configure_logging
from raspbot.settings import settings

logger = configure_logging(name=__name__)


async def start_bot():
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()

    dp.include_routers(users_router, start_router, routes_router, timetable_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting the bot.")
    await dp.start_polling(bot)
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(start_bot())
