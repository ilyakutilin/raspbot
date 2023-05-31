from aiogram.filters.callback_data import CallbackData

SELECT_DEPARTURE = "select_departure"
MISSING_POINT = "missing_point"


class PointsCallbackFactory(CallbackData, prefix="pointselect"):
    is_departure: bool
    is_station: bool
    yandex_code: str
