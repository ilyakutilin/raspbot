from aiogram.filters.callback_data import CallbackData

SELECT_DEPARTURE = "select_departure"
MISSING_POINT = "missing_point_{dep_or_dest}"


class PointsCallbackFactory(CallbackData, prefix="pointselect"):
    is_departure: bool
    is_station: bool
    point_id: int
