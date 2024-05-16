from aiogram import Bot

from raspbot.core.logging import configure_logging
from raspbot.settings import settings

logger = configure_logging(__name__)


async def send_telegram_message_to_admin(
    message: str,
    chat_id: int = settings.TELEGRAM_CHAT_ID,
    bot: Bot = Bot(token=settings.TELEGRAM_TOKEN),
) -> None:
    """Sends a message to the chat."""
    logger.info(
        f"Sending message to chat {chat_id} from bot {bot.get_me().username}: {message}"
    )
    await bot.send_message(chat_id=chat_id, text=message)
