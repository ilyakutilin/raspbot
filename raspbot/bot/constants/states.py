from aiogram.fsm.state import State, StatesGroup


class RouteState(StatesGroup):
    """States of the route."""

    selecting_departure_point = State()
    selecting_destination_point = State()
    getting_timetable_between_points = State()


class TimetableState(StatesGroup):
    """States of the timetable."""

    exact_departure_info = State()
    other_date = State()
