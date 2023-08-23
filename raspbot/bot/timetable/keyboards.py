from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging, log
from raspbot.db.routes.schema import ThreadResponse
from raspbot.settings import settings

logger = configure_logging(name=__name__)


@log(logger)
def get_closest_departures_keyboard(
    departures_list: list[ThreadResponse],
    route_id: int,
    buttons_qty: int = settings.INLINE_DEPARTURES_QTY,
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for dep in departures_list:
        builder.button(
            text=dep.str_time,
            callback_data=clb.DepartureTimeCallbackFactory(
                dep_time=dep.str_time.replace(":", "-")
            ),
        )
    remainder = len(departures_list) % buttons_qty
    if remainder != 0:
        for i in range(buttons_qty - remainder):
            builder.button(text="", callback_data="empty_button")
    builder.button(
        text=btn.TOMORROW,
        callback_data=clb.TomorrowTimetableCallbackFactory(route_id=route_id),
    )
    builder.button(
        text=btn.OTHER_DATE,
        callback_data=clb.OtherDateTimetableCallbackFactory(route_id=route_id),
    )
    button_groups = [buttons_qty] * -(-len(departures_list) // buttons_qty)
    builder.adjust(*button_groups, 2)
    return builder.as_markup()
