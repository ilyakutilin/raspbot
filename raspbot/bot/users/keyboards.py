from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import Favorite, Recent

logger = configure_logging(name=__name__)


@log(logger)
def get_recent_command_keyboard(
    user_recent: list[Recent],
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for recent in user_recent:
        builder.button(
            text=recent.route.short,
            callback_data=clb.RecentCallbackFactory(route_id=recent.route_id),
        )
    builder.adjust(1)
    return builder.as_markup()


@log(logger)
def add_recent_to_fav_keyboard(user_recent: list[Recent]) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for recent in user_recent:
        builder.button(
            text=recent.route.short,
            callback_data=clb.RecentToFavCallbackFactory(route_id=recent.route_id),
        )
    callback_arg = "_".join([str(recent.id) for recent in user_recent])
    builder.button(
        text=btn.ADD_ALL_RECENT_TO_FAV,
        callback_data=clb.AllRecentToFavCallbackFactory(route_ids=callback_arg),
    )
    builder.button(text=btn.NEW_SEARCH, callback_data=clb.NEW_SEARCH)
    builder.adjust(1)
    return builder.as_markup()


@log(logger)
def get_fav_command_keyboard(user_fav: list[Favorite]) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for fav in user_fav:
        builder.button(
            text=fav.route.short,
            callback_data=clb.FavCallbackFactory(route_id=fav.route_id),
        )
    builder.adjust(1)
    return builder.as_markup()
