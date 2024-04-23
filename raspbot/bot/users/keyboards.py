from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import Recent

logger = configure_logging(name=__name__)


@log(logger)
def get_fav_or_recent_keyboard(
    fav_or_recent_list: list[Recent],
) -> types.InlineKeyboardMarkup:
    """Keyboard for favorite or recent routes."""
    builder = InlineKeyboardBuilder()
    for element in fav_or_recent_list:
        builder.button(
            text=element.route.short,
            callback_data=clb.GetTimetableCallbackFactory(recent_id=element.id),
        )
    builder.button(text=btn.NEW_SEARCH, callback_data=clb.NEW_SEARCH)
    builder.adjust(1)
    return builder.as_markup()


@log(logger)
def add_recent_to_fav_keyboard(user_recent: list[Recent]) -> types.InlineKeyboardMarkup:
    """Keyboard for adding recent routes to favorite."""
    builder = InlineKeyboardBuilder()
    for recent in user_recent:
        builder.button(
            text=recent.route.short,
            callback_data=clb.RecentToFavCallbackFactory(recent_id=recent.id),
        )
    callback_arg = "_".join([str(recent.id) for recent in user_recent])
    builder.button(
        text=btn.ADD_ALL_RECENT_TO_FAV,
        callback_data=clb.AllRecentToFavCallbackFactory(recent_ids=callback_arg),
    )
    builder.button(text=btn.NEW_SEARCH, callback_data=clb.NEW_SEARCH)
    ones = [1] * len(user_recent)
    builder.adjust(*ones, 2)
    return builder.as_markup()
