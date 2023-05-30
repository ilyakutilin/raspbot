import asyncio

from aiogram import Bot, Dispatcher

from raspbot.core.logging import configure_logging
from raspbot.settings import settings

# from handlers import different_types, questions


logger = configure_logging(name=__name__)


async def start_bot():
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    logger.info("Bot started.")


if __name__ == "__main__":
    asyncio.run(start_bot())
