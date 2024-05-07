from aiogram import Bot

from raspbot.settings import settings


async def send_telegram_message_to_admin(
    message: str,
    chat_id: int = settings.TELEGRAM_CHAT_ID,
    bot: Bot = Bot(token=settings.TELEGRAM_TOKEN),
) -> None:
    """Sends a message to the chat."""
    await bot.send_message(chat_id=chat_id, text=message)
