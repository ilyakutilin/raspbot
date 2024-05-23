from aiogram import Router, types
from aiogram.filters import Command

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import messages as msg
from raspbot.bot.utils import get_command_user
from raspbot.core.logging import configure_logging

logger = configure_logging(name=__name__)

router = Router()


kb = [
    [
        types.KeyboardButton(text=btn.NEW_SEARCH_COMMAND),
        types.KeyboardButton(text=btn.RECENTS_COMMAND),
        types.KeyboardButton(text=btn.FAVORITES_COMMAND),
    ],
]
keyboard = types.ReplyKeyboardMarkup(
    keyboard=kb,
    resize_keyboard=True,
)


@router.message(Command("start"))
async def start_command(message: types.Message):
    """User: issues /start command. Bot: please input the departure point."""
    assert message.from_user
    user, new_user = await get_command_user(
        command="start",
        message=message,
        reply_text=msg.GREETING_NEW_USER.format(
            first_name=message.from_user.first_name
        ),
        reply_markup=keyboard,
    )

    if not new_user:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /start command. "
            "Greeting existing user."
        )
        await message.answer(
            msg.GREETING_EXISTING_USER.format(first_name=user.first_name),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
