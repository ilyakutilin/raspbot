from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    # TODO: Complete add_recent_to_fav_keyboard
    pass


@log(logger)
def get_fav_command_keyboard(user_fav: list[Favorite]) -> types.InlineKeyboardMarkup:
    # TODO: Complete get_fav_command_keyboard
    pass
