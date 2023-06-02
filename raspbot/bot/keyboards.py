from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import callback
from raspbot.bot.constants.text import btn
from raspbot.db.stations.schema import PointResponse
from raspbot.services.shortener import get_short_region_title


def get_start_keyboard():
    buttons = [
        [
            types.InlineKeyboardButton(
                text=btn.NEW_SEARCH, callback_data=callback.SELECT_DEPARTURE
            )
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_point_choice_keyboard(
    points: list[PointResponse], is_departure: bool
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for point in points:
        point_type = "ст." if point.is_station else "г."
        region_title = get_short_region_title(region_title=point.region_title)
        builder.button(
            text=f"{point_type} {point.title}, {region_title}",
            callback_data=callback.PointsCallbackFactory(
                is_departure=is_departure,
                is_station=point.is_station,
                point_id=point.id,
            ),
        )
    builder.button(
        text=btn.MY_POINT_IS_NOT_HERE,
        callback_data=callback.MISSING_POINT.format(dep_or_dest=str(int(is_departure))),
    )
    builder.adjust(1)
    return builder.as_markup()
