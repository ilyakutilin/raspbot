from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import callback as clb
from raspbot.db.routes.schema import PointResponse
from raspbot.services.shorteners.short_point import get_short_point_type
from raspbot.services.shorteners.short_region import get_short_region_title


def get_point_choice_keyboard(
    points: list[PointResponse], is_departure: bool, last_chunk: bool = True
) -> types.InlineKeyboardMarkup:
    """Keyboard listing potential points matching the search pattern."""
    builder = InlineKeyboardBuilder()
    for point in points:
        point_type = get_short_point_type(point.point_type)
        region_title = get_short_region_title(region_title=point.region_title)
        builder.button(
            text=f"{point_type} {point.title}, {region_title}",
            callback_data=clb.PointsCallbackFactory(
                is_departure=is_departure,
                point_id=point.id,
            ),
        )
    if not last_chunk:
        builder.button(
            text=btn.MORE_POINT_CHOICES,
            callback_data=clb.MorePointCunksCallbackFactory(is_departure=is_departure),
        )
    else:
        builder.button(
            text=btn.MY_POINT_IS_NOT_HERE,
            callback_data=clb.MissingPointCallbackFactory(is_departure=is_departure),
        )
    builder.adjust(1)
    return builder.as_markup()


def get_single_point_confirmation_keyboard(point: PointResponse, is_departure: bool):
    """Keyboard for confirming correct matching if only one point is found."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=btn.CONFIRM_SINGE_POINT,
        callback_data=clb.PointsCallbackFactory(
            is_departure=is_departure,
            point_id=point.id,
        ),
    )
    builder.button(
        text=btn.DECLINE_SINGLE_POINT,
        callback_data=clb.MissingPointCallbackFactory(is_departure=is_departure),
    )
    builder.adjust(1)
    return builder.as_markup()
