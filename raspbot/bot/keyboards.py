from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants.text import btn
from raspbot.db.stations.schema import PointResponse
from raspbot.services.shortener import get_short_region_title


class PointChoiceKeyboard:
    def __init__(self, points: list[PointResponse], is_departure: bool):
        self.points = points
        self.is_departure = is_departure
        self.builder = InlineKeyboardBuilder()

    def _create_point_button_list(self, selected_points: list[PointResponse]):
        for point in selected_points:
            point_type = "ст." if point.is_station else "г."
            region_title = get_short_region_title(region_title=point.region_title)
            self.builder.button(
                text=f"{point_type} {point.title}, {region_title}",
                callback_data=clb.PointsCallbackFactory(
                    is_departure=self.is_departure,
                    is_station=point.is_station,
                    point_id=point.id,
                ),
            )

    def _create_button_for_missing(
        self, button_text: str, exact: bool
    ) -> types.InlineKeyboardMarkup:
        self.builder.button(
            text=button_text,
            callback_data=clb.MissingPointCallbackFactory(
                is_departure=self.is_departure, exact=exact
            ),
        )
        self.builder.adjust(1)
        return self.builder.as_markup()

    def get_exact_keyboard(self) -> types.InlineKeyboardMarkup:
        exact_points: list[PointResponse] = [
            point for point in self.points if point.exact
        ]
        self._create_point_button_list(selected_points=exact_points)
        return self._create_button_for_missing(
            button_text=btn.MY_POINT_IS_NOT_HERE, exact=True
        )

    def get_inexact_keyboard(self) -> types.InlineKeyboardMarkup:
        self._create_point_button_list(selected_points=self.points)
        return self._create_button_for_missing(
            button_text=btn.MY_POINT_IS_STILL_NOT_HERE, exact=False
        )
