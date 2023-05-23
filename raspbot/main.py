from raspbot.bot.bot import create_bot
from raspbot.core.logging import configure_logging

logger = configure_logging(name=__name__)


if __name__ == "__main__":
    create_bot().run_polling()
    logger.info("Bot started.")
