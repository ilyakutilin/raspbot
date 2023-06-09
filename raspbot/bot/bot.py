import asyncio

from aiogram import Bot, Dispatcher

from raspbot.bot.routes.handlers import router
from raspbot.core.logging import configure_logging
from raspbot.settings import settings

logger = configure_logging(name=__name__)


async def start_bot():
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()

    dp.include_routers(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    logger.info("Bot started.")


if __name__ == "__main__":
    asyncio.run(start_bot())
