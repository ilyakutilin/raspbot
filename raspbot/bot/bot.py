from telegram.ext import AIORateLimiter, Application, CommandHandler

from raspbot.bot.handlers import start_command
from raspbot.config import settings
from raspbot.config.logging import configure_logging

logger = configure_logging(name=__name__)


def create_bot() -> Application:
    bot = (
        Application.builder()
        .token(settings.TELEGRAM_TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    bot.add_handler(CommandHandler("start", start_command))
    return bot


if __name__ == "__main__":
    create_bot().run_polling()
    logger.info("Bot started.")
