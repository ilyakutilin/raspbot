from aiogram import Router, types
from aiogram.filters import Command

from raspbot.bot.constants import messages as msg
from raspbot.bot.start import keyboard as start_keyboard
from raspbot.bot.users.keyboards import (
    add_recent_to_fav_keyboard,
    get_fav_command_keyboard,
    get_recent_command_keyboard,
)
from raspbot.core.logging import configure_logging
from raspbot.services.users import (
    create_user,
    get_user_fav,
    get_user_from_db,
    get_user_recent,
)

logger = configure_logging(name=__name__)

router = Router()


@router.message(Command("recent"))
async def recent_command(message: types.Message):
    "Команда /recent."
    user = await get_user_from_db(telegram_id=message.from_user.id)
    if not user:
        user = await create_user(tg_user=message.from_user)
        await message.answer(
            text=msg.NO_RECENT, reply_markup=start_keyboard, parse_mode="HTML"
        )
        return
    user_recent = await get_user_recent(user=user)
    if not user_recent:
        await message.answer(
            text=msg.NO_RECENT, reply_markup=start_keyboard, parse_mode="HTML"
        )
    else:
        await message.answer(
            text=msg.RECENT_LIST,
            reply_markup=get_recent_command_keyboard(user_recent=user_recent),
        )


@router.message(Command("fav"))
async def fav_command(message: types.Message):
    """Команда /fav."""
    user = await get_user_from_db(telegram_id=message.from_user.id)
    if not user:
        user = await create_user(tg_user=message.from_user)
    user_recent = await get_user_recent(user=user)
    if not user_recent:
        await message.answer(
            text=msg.NO_FAV_NO_RECENT, reply_markup=start_keyboard, parse_mode="HTML"
        )
        return
    user_fav = await get_user_fav(user=user)
    if not user_fav:
        await message.answer(
            text=msg.NO_FAV_YES_RECENT,
            reply_markup=add_recent_to_fav_keyboard,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text=msg.FAV_LIST,
            reply_markup=get_fav_command_keyboard(user_fav=user_fav),
        )
