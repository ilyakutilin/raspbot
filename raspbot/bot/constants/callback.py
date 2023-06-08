from aiogram.filters.callback_data import CallbackData

MISSING_POINT = "missing_point_{dep_or_dest}"


class MissingPointCallbackFactory(CallbackData, prefix="missing_point"):
    is_departure: bool


class PointsCallbackFactory(CallbackData, prefix="pointselect"):
    is_departure: bool
    is_station: bool
    point_id: int
