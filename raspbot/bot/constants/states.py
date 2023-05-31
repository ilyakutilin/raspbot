from aiogram.fsm.state import State, StatesGroup


class Route(StatesGroup):
    choosing_departure_point = State()
    choosing_destination_point = State()
    choosing_point_from_multiple = State()
    getting_timetable_between_points = State()
