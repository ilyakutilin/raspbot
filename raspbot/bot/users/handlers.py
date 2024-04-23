from aiogram import Router, types
from aiogram.filters import Command

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.start import keyboard as start_keyboard
from raspbot.bot.users.keyboards import (
    add_recent_to_fav_keyboard,
    get_fav_or_recent_keyboard,
)
from raspbot.core.logging import configure_logging
from raspbot.db.models import Route
from raspbot.services.routes import RouteRetriever
from raspbot.services.users import (
    add_recent_to_fav,
    create_user,
    get_user_fav,
    get_user_from_db,
    get_user_recent,
)

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


@router.message(Command("recent"))
async def recent_command(message: types.Message):
    """Команда /recent."""
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
            reply_markup=get_fav_or_recent_keyboard(fav_or_recent_list=user_recent),
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
            reply_markup=add_recent_to_fav_keyboard(user_recent=user_recent),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text=msg.FAV_LIST,
            reply_markup=get_fav_or_recent_keyboard(fav_or_recent_list=user_fav),
        )


@router.callback_query(clb.RecentToFavCallbackFactory.filter())
async def add_recent_to_fav_callback(
    callback: types.CallbackQuery, callback_data: clb.RecentToFavCallbackFactory
):
    """User: clicks on the 'add to fav' button. Bot: added to favorites."""
    recent = await add_recent_to_fav(recent_id=callback_data.recent_id)
    route: Route = await route_retriever.get_route_by_recent(recent_id=recent.id)
    await callback.message.answer(text=msg.ROUTE_ADDED_TO_FAV.format(route=route))
    await callback.answer()


@router.callback_query(clb.AllRecentToFavCallbackFactory.filter())
async def add_all_recent_to_fav_callback(
    callback: types.CallbackQuery, callback_data: clb.AllRecentToFavCallbackFactory
):
    """User: clicks on the 'add all to fav' button. Bot: added to favorites."""
    recent_ids = callback_data.recent_ids.split(sep="_")
    for recent_id in recent_ids:
        await add_recent_to_fav(recent_id=int(recent_id))
    msg_text = str(msg.MultipleToFav(amount=len(recent_ids)))
    await callback.message.answer(text=msg_text)
    await callback.answer()
