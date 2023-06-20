from aiogram.filters.callback_data import CallbackData


class MorePointCunksCallbackFactory(CallbackData, prefix="more_point_chunks"):
    is_departure: bool


class MyPointCallbackFactory(CallbackData, prefix="mypoint"):
    confirm: bool
    is_departure: bool


class MissingPointCallbackFactory(CallbackData, prefix="missing_point"):
    is_departure: bool


class PointsCallbackFactory(CallbackData, prefix="pointselect"):
    is_departure: bool
    point_id: int
