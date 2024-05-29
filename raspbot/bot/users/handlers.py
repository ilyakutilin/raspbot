from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.start.keyboards import back_to_start_keyboard, start_keyboard
from raspbot.bot.start.utils import get_command_user
from raspbot.bot.users.keyboards import (
    add_recent_to_fav_keyboard,
    get_fav_or_recent_keyboard,
)
from raspbot.core import exceptions as exc
from raspbot.core.email import send_email_async
from raspbot.core.logging import configure_logging
from raspbot.db.models import RouteORM
from raspbot.services.routes import RouteRetriever
from raspbot.services.users import (
    add_recent_to_fav,
    get_recent_by_route,
    get_user_fav,
    get_user_from_db_or_raise,
    get_user_recent,
)

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


@router.message(Command("recent"))
async def recent_command(message: types.Message):
    """User: issues /recent command. Bot: lists recents or advises otherwise."""
    user, _ = await get_command_user(
        command="recent",
        message=message,
        reply_text=msg.NO_RECENT,
        reply_markup=start_keyboard,
    )

    try:
        user_recent = await get_user_recent(user=user)
    except Exception as e:
        logger.exception(e)
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
        await send_email_async(e)

    if not user_recent:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /recent command. "
            "User has no recent. Replying."
        )
        await message.answer(
            text=msg.NO_RECENT, reply_markup=start_keyboard, parse_mode="HTML"
        )

    else:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /recent command. "
            "Replying."
        )
        await message.answer(
            text=msg.RECENT_LIST,
            reply_markup=get_fav_or_recent_keyboard(fav_or_recent_list=user_recent),
        )


@router.message(Command("fav"))
async def fav_command(message: types.Message):
    """User: issues /fav command. Bot: lists favs or advises otherwise."""
    user, _ = await get_command_user(
        command="fav",
        message=message,
    )

    try:
        user_recent = await get_user_recent(user=user)
    except Exception as e:
        logger.exception(e)
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
        await send_email_async(e)

    if not user_recent:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /fav command. "
            "User has no recent, therefore no fav. Replying."
        )
        await message.answer(
            text=msg.NO_FAV_NO_RECENT, reply_markup=start_keyboard, parse_mode="HTML"
        )
        return

    try:
        user_fav = await get_user_fav(user=user)
    except Exception as e:
        logger.exception(e)
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
        await send_email_async(e)

    if not user_fav:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /fav command. "
            "User has recent, but no fav. Replying."
        )
        await message.answer(
            text=msg.NO_FAV_YES_RECENT,
            reply_markup=add_recent_to_fav_keyboard(user_recent=user_recent),
            parse_mode="HTML",
        )

    else:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /fav command. "
            "Replying."
        )
        await message.answer(
            text=msg.FAV_LIST,
            reply_markup=get_fav_or_recent_keyboard(fav_or_recent_list=user_fav),
        )


@router.callback_query(clb.RouteToFavCallbackFactory.filter())
async def add_route_to_fav_callback(
    callback: types.CallbackQuery,
    callback_data: clb.RouteToFavCallbackFactory,
    state: FSMContext,
):
    """User: clicks on the 'add to fav' button. Bot: added to favorites."""
    tg_user_id = callback.from_user.id

    assert isinstance(callback.message, types.Message)
    try:
        user = await get_user_from_db_or_raise(telegram_id=tg_user_id)
    except exc.NotFoundError as e:
        text = (
            f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
            f"was not found in the database. Route with ID {callback_data.route_id} "
            "cannot be added to favorites."
        )
        logger.error(text)
        await send_email_async(e)
        await callback.message.answer(msg.ERROR, reply_markup=back_to_start_keyboard())

    recent = await get_recent_by_route(user_id=user.id, route_id=callback_data.route_id)
    fav = await add_recent_to_fav(recent_id=recent.id)
    route = await route_retriever.get_route_from_db(route_id=fav.route_id)

    logger.info(
        f"User {user.full_name} TGID {user.telegram_id} "
        f"added the route '{route}' to favorites."
    )
    await callback.answer(
        text=msg.ROUTE_ADDED_TO_FAV.format(route=route), show_alert=True
    )


@router.callback_query(clb.RecentToFavCallbackFactory.filter())
async def add_recent_to_fav_callback(
    callback: types.CallbackQuery, callback_data: clb.RecentToFavCallbackFactory
):
    """User: clicks on the recent route. Bot: added to favorites."""
    recent = await add_recent_to_fav(recent_id=callback_data.recent_id)
    route: RouteORM = await route_retriever.get_route_by_recent(recent_id=recent.id)

    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        f"added the route '{route}' to favorites."
    )
    assert isinstance(callback.message, types.Message)
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

    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        f"added all their recent routes to favorites."
    )
    assert isinstance(callback.message, types.Message)
    await callback.message.answer(text=msg_text)
    await callback.answer()
