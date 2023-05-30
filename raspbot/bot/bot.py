from telegram.ext import AIORateLimiter, Application, CallbackQueryHandler

from raspbot.bot.handlers import choose_station_from_multiple, conv_handler
from raspbot.core.logging import configure_logging
from raspbot.settings import settings

logger = configure_logging(name=__name__)


def create_bot() -> Application:
    bot = (
        Application.builder()
        .token(settings.TELEGRAM_TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    bot.add_handler(conv_handler)
    bot.add_handler(
        CallbackQueryHandler(choose_station_from_multiple, pattern=r".+_station_\d+")
    )
    return bot


if __name__ == "__main__":
    create_bot().run_polling()
    logger.info("Bot started.")
