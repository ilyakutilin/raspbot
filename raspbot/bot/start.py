from aiogram import Router, types
from aiogram.filters import Command

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import messages as msg
from raspbot.core.logging import configure_logging
from raspbot.services.users import create_user, get_user_from_db

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
    from_user = message.from_user
    if not from_user:
        return
    user = await get_user_from_db(telegram_id=from_user.id)
    if not user:
        logger.info(
            f"New user detected: {from_user.full_name}, "
            f"telegram id = {from_user.id}. Adding to DB."
        )
        user = await create_user(tg_user=from_user)
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /start command. "
            "Greeting new user."
        )
        await message.answer(
            msg.GREETING_NEW_USER.format(first_name=from_user.first_name),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /start command. "
            "Greeting existing user."
        )
        await message.answer(
            msg.GREETING_EXISTING_USER.format(first_name=user.first_name),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
