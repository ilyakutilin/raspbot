from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging, log

logger = configure_logging(name=__name__)


@log(logger)
def get_closest_departures_keyboard(
    departures_list: list[str],
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for dep in departures_list:
        builder.button(
            text=dep, callback_data=clb.DepartureTimeCallbackFactory(dep_time=dep)
        )
