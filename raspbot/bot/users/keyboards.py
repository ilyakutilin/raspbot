from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging, log
from raspbot.db.users.models import Recent

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
