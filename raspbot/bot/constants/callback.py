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


class GetTimetableCallbackFactory(CallbackData, prefix="recent"):
    recent_id: int


class RecentToFavCallbackFactory(CallbackData, prefix="recent_to_fav"):
    recent_id: int


class AllRecentToFavCallbackFactory(CallbackData, prefix="all_recent_to_fav"):
    recent_ids: str


class DepartureUIDCallbackFactory(CallbackData, prefix="dep_uid"):
    uid: str


class EndOfTheDayTimetableCallbackFactory(CallbackData, prefix="till_the_end"):
    route_id: int


class TomorrowTimetableCallbackFactory(CallbackData, prefix="tomorrow"):
    route_id: int


class OtherDateTimetableCallbackFactory(CallbackData, prefix="other_date"):
    route_id: int
