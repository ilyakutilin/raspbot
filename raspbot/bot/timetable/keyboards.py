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
    buttons_qty_in_row: int = settings.INLINE_DEPARTURES_QTY,
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for dep in departures_list:
        builder.button(
            text=dep.str_time,
            callback_data=clb.DepartureUIDCallbackFactory(
                uid=dep.uid, route_id=route_id
            ),
        )
    remainder = len(departures_list) % buttons_qty_in_row
    if remainder != 0:
        for i in range(buttons_qty_in_row - remainder):
            builder.button(text="", callback_data="empty_button")
    builder.button(
        text=btn.TILL_THE_END_OF_THE_DAY,
        callback_data=clb.EndOfTheDayTimetableCallbackFactory(route_id=route_id),
    )
    builder.button(
        text=btn.TOMORROW,
        callback_data=clb.TomorrowTimetableCallbackFactory(route_id=route_id),
    )
    builder.button(
        text=btn.OTHER_DATE,
        callback_data=clb.OtherDateTimetableCallbackFactory(route_id=route_id),
    )
    button_rows = [buttons_qty_in_row] * -(-len(departures_list) // buttons_qty_in_row)
    builder.adjust(*button_rows, 1, 2)
    return builder.as_markup()


@log(logger)
def get_separate_departure_keyboard(
    departures_list: list[ThreadResponse],
    this_departure: ThreadResponse,
    route_id: int,
    buttons_qty_in_row: int = settings.INLINE_DEPARTURES_QTY,
) -> types.InlineKeyboardMarkup:
    markup: types.InlineKeyboardMarkup = get_closest_departures_keyboard(
        departures_list=departures_list,
        route_id=route_id,
        buttons_qty_in_row=buttons_qty_in_row,
    )
    for row in markup.inline_keyboard:
        for button in row:
            uid = button.callback_data.split(":")[1].strip()
            if uid == this_departure.uid:
                button.text = f"[-- {button.text} --]"
                return markup
    return markup
