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
    user = await get_user_from_db(telegram_id=message.from_user.id)
    if not user:
        user = await create_user(tg_user=message.from_user)
        await message.answer(
            msg.GREETING_NEW_USER.format(first_name=message.from_user.first_name),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            msg.GREETING_EXISTING_USER.format(first_name=user.first_name),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
