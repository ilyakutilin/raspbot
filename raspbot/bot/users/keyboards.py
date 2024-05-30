from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import RecentORM

logger = configure_logging(name=__name__)


@log(logger)
def get_recent_keyboard(
    recent_list: list[RecentORM],
) -> types.InlineKeyboardMarkup:
    """Keyboard for favorite or recent routes."""
    builder = InlineKeyboardBuilder()
    for element in recent_list:
        builder.button(
            text=element.route.short,  # type: ignore
            callback_data=clb.GetTimetableCallbackFactory(recent_id=element.id),
        )
    builder.button(text=btn.NEW_SEARCH, callback_data=clb.NEW_SEARCH)
    builder.adjust(1)
    logger.info(f"recent_keyboard contains {len(set(builder.buttons))} buttons.")
    return builder.as_markup()


@log(logger)
def get_fav_keyboard(
    fav_list: list[RecentORM],
    for_deletion: bool = False,
    recents_not_in_fav: bool = False,
) -> types.InlineKeyboardMarkup:
    """Keyboard for favorite or recent routes."""
    builder = InlineKeyboardBuilder()

    clb_factory = (
        clb.DeleteFavCallbackFactory
        if for_deletion
        else clb.GetTimetableCallbackFactory
    )

    for element in fav_list:
        builder.button(
            text=element.route.short,  # type: ignore
            callback_data=clb_factory(recent_id=element.id),
        )
    if not for_deletion:
        if recents_not_in_fav:
            builder.button(
                text=btn.ADD_MORE_TO_FAV,
                callback_data=clb.MORE_RECENTS_TO_FAV,
            )
        builder.button(text=btn.DELETE_FAVS, callback_data=clb.FAVS_FOR_DELETION)
    builder.button(text=btn.NEW_SEARCH, callback_data=clb.NEW_SEARCH)
    builder.adjust(1)
    logger.info(f"fav_keyboard contains {len(set(builder.buttons))} buttons.")
    return builder.as_markup()


@log(logger)
def add_recent_to_fav_keyboard(
    user_recent: list[RecentORM],
) -> types.InlineKeyboardMarkup:
    """Keyboard for adding recent routes to favorite."""
    builder = InlineKeyboardBuilder()
    for recent in user_recent:
        builder.button(
            text=recent.route.short,  # type: ignore
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
    logger.info(f"recent_to_fav_keyboard contains {len(set(builder.buttons))} buttons.")
    return builder.as_markup()
