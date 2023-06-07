from aiogram.fsm.state import State, StatesGroup


class Route(StatesGroup):
    selecting_departure_point = State()
    selecting_destination_point = State()
    getting_timetable_between_points = State()
