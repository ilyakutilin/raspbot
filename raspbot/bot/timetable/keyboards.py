from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging, log
from raspbot.db.routes.schema import ThreadResponsePD
from raspbot.services.timetable import Timetable
from raspbot.settings import settings

logger = configure_logging(name=__name__)


@log(logger)
async def get_today_departures_keyboard(
    timetable_obj: Timetable,
    buttons_qty_in_row: int = settings.INLINE_DEPARTURES_QTY,
) -> types.InlineKeyboardMarkup:
    """Keyboard with today's departures."""
    builder = InlineKeyboardBuilder()
    timetable = await timetable_obj.timetable
    logger.debug(f"Timetable len: {len(timetable)}")
    route_id = timetable_obj.route.id
    for dep in timetable[: settings.CLOSEST_DEP_LIMIT]:
        builder.button(
            text=dep.str_time,
            callback_data=clb.DepartureUIDCallbackFactory(uid=dep.uid),
        )
    remainder = len(timetable) % buttons_qty_in_row
    if remainder != 0:
        for i in range(buttons_qty_in_row - remainder):
            builder.button(text="", callback_data="empty_button")
    timetable_obj_length = await timetable_obj.length
    if timetable_obj_length > len(timetable):
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
    button_rows = [buttons_qty_in_row] * -(-len(timetable) // buttons_qty_in_row)
    if btn.TILL_THE_END_OF_THE_DAY in [button.text for button in builder.buttons]:
        builder.adjust(*button_rows, 1, 2)
    else:
        builder.adjust(*button_rows, 2)
    return builder.as_markup()


@log(logger)
async def get_date_departures_keyboard(
    route_id: int,
) -> types.InlineKeyboardMarkup:
    """Keyboard with departures on a certain date."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=btn.OTHER_DATE,
        callback_data=clb.OtherDateTimetableCallbackFactory(route_id=route_id),
    )
    builder.adjust(1)
    return builder.as_markup()


@log(logger)
async def get_separate_departure_keyboard(
    timetable_obj: Timetable,
    this_departure: ThreadResponsePD,
    buttons_qty_in_row: int = settings.INLINE_DEPARTURES_QTY,
) -> types.InlineKeyboardMarkup:
    """Keyboard with info about a particular departure."""
    markup: types.InlineKeyboardMarkup = await get_today_departures_keyboard(
        timetable_obj=timetable_obj,
        buttons_qty_in_row=buttons_qty_in_row,
    )
    for row in markup.inline_keyboard:
        for button in row:
            callpback_split = button.callback_data.split(":")
            callback_prefix = callpback_split[0]
            uid = callpback_split[1] if callback_prefix == clb.DEP_UID else None
            if uid == this_departure.uid and not None:
                button.text = f"[-{button.text}-]"
                button.callback_data = clb.SAME_DEPARTURE
                return markup
    return markup
