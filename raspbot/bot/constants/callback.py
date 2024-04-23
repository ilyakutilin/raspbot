from aiogram.filters.callback_data import CallbackData

NEW_SEARCH = "new_search"


class MorePointCunksCallbackFactory(CallbackData, prefix="more_point_chunks"):
    """More point chunks callback factory."""

    is_departure: bool


class MyPointCallbackFactory(CallbackData, prefix="mypoint"):
    """My point callback factory."""

    confirm: bool
    is_departure: bool


class MissingPointCallbackFactory(CallbackData, prefix="missing_point"):
    """Missing point callback factory."""

    is_departure: bool


class PointsCallbackFactory(CallbackData, prefix="pointselect"):
    """Points callback factory."""

    is_departure: bool
    point_id: int


class GetTimetableCallbackFactory(CallbackData, prefix="recent"):
    """Get timetable callback factory."""

    recent_id: int


class RecentToFavCallbackFactory(CallbackData, prefix="recent_to_fav"):
    """Get timetable callback factory."""

    recent_id: int


class AllRecentToFavCallbackFactory(CallbackData, prefix="all_recent_to_fav"):
    """Get timetable callback factory."""

    recent_ids: str


DEP_UID = "dep_uid"


class DepartureUIDCallbackFactory(CallbackData, prefix=DEP_UID):
    """Departure UID callback factory."""

    uid: str


SAME_DEPARTURE = "same_dep"


class EndOfTheDayTimetableCallbackFactory(CallbackData, prefix="till_the_end"):
    """Callback factory for the timetable till the end of the curent day."""

    route_id: int


class TomorrowTimetableCallbackFactory(CallbackData, prefix="tomorrow"):
    """Callback factory for the timetable for tomorrow."""

    route_id: int


class OtherDateTimetableCallbackFactory(CallbackData, prefix="other_date"):
    """Callback factory for the timetable for arbitrary date."""

    route_id: int
