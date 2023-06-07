from aiogram.filters.callback_data import CallbackData


class PointsCallbackFactory(CallbackData, prefix="pointselect"):
    is_departure: bool
    is_station: bool
    point_id: int


class MissingPointCallbackFactory(CallbackData, prefix="missing_point"):
    is_departure: bool
    exact: bool
