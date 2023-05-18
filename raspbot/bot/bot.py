from telegram.ext import AIORateLimiter, Application

from raspbot.bot.handlers import conv_handler
from raspbot.config.logging import configure_logging
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
    return bot


if __name__ == "__main__":
    create_bot().run_polling()
    logger.info("Bot started.")
