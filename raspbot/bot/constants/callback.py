from aiogram.filters.callback_data import CallbackData

NEW_SEARCH = "new_search"


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


class RecentCallbackFactory(CallbackData, prefix="recent"):
    route_id: int


class RecentToFavCallbackFactory(CallbackData, prefix="recent_to_fav"):
    route_id: int


class AllRecentToFavCallbackFactory(CallbackData, prefix="all_recent_to_fav"):
    route_ids: str


class FavCallbackFactory(CallbackData, prefix="fav"):
    route_id: int
