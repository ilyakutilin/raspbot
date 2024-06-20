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
    route_is_in_user_fav: bool = False,
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

    button_rows = [buttons_qty_in_row] * -(
        -len(timetable[: settings.CLOSEST_DEP_LIMIT]) // buttons_qty_in_row
    )

    timetable_obj_length = await timetable_obj.length
    if timetable_obj_length > len(timetable):
        builder.button(
            text=btn.TILL_THE_END_OF_THE_DAY,
            callback_data=clb.EndOfTheDayTimetableCallbackFactory(route_id=route_id),
        )
        button_rows.append(1)

    builder.button(
        text=btn.TOMORROW,
        callback_data=clb.TomorrowTimetableCallbackFactory(route_id=route_id),
    )
    builder.button(
        text=btn.OTHER_DATE,
        callback_data=clb.OtherDateTimetableCallbackFactory(route_id=route_id),
    )
    button_rows.append(2)

    if not route_is_in_user_fav:
        builder.button(
            text=btn.ADD_TO_FAV,
            callback_data=clb.RouteToFavCallbackFactory(route_id=route_id),
        )
        button_rows.append(1)

    builder.button(text=btn.START, callback_data=clb.START)
    button_rows.append(1)

    builder.adjust(*button_rows)

    logger.info(f"Keyboard {__name__} contains {len(set(builder.buttons))} buttons.")
    return builder.as_markup()


@log(logger)
async def get_date_departures_keyboard(
    route_id: int,
    route_is_in_user_fav: bool = False,
) -> types.InlineKeyboardMarkup:
    """Keyboard with departures on a certain date."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=btn.OTHER_DATE,
        callback_data=clb.OtherDateTimetableCallbackFactory(route_id=route_id),
    )
    if not route_is_in_user_fav:
        builder.button(
            text=btn.ADD_TO_FAV,
            callback_data=clb.RouteToFavCallbackFactory(route_id=route_id),
        )
    builder.button(text=btn.START, callback_data=clb.START)
    builder.adjust(1)

    logger.info(f"Keyboard {__name__} contains {len(set(builder.buttons))} buttons.")
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
        # This is a kludge - we don't need 'Add to fav' button for the departure view,
        # so we set this to True regardless of whether it's actually true,
        # just to get rid of the button.
        route_is_in_user_fav=True,
    )
    for row in markup.inline_keyboard:
        for button in row:
            assert button.callback_data
            callpback_split = button.callback_data.split(":")
            callback_prefix = callpback_split[0]
            uid = callpback_split[1] if callback_prefix == clb.DEP_UID else None
            if uid == this_departure.uid and not None:
                button.text = f"[-{button.text}-]"
                button.callback_data = clb.SAME_DEPARTURE
                return markup
    return markup
