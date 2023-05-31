from typing import NamedTuple


class Message(NamedTuple):
    GREETING: str = "Привет, {name}! 👋 \n\nЯ подскажу расписание электричек."
    INPUT_DEPARTURE_POINT: str = "Введите пункт отправления (город или станцию):"
    INPUT_DESTINATION_POINT: str = "Введите пункт назначения (город или станцию):"
    POINT_NOT_FOUND: str = (
        "Не найдено такой станции или города. Попробуйте ввести по-другому:"
    )
    SINGLE_POINT_FOUND: str = (
        "Пункт отправления - {departure_point_type} {departure_point_name}, "
        "{departure_point_region}."
    )
    MULTIPLE_POINTS_FOUND: str = (
        "Было найдено несколько пунктов, удовлетворяющих вашему запросу.\n"
        "Выберите нужный пункт (город или станцию) из списка ниже:"
    )
    SEARCHING_FOR_TIMETABLE: str = (
        "Ищем раписание между {departure_point_type} {departure_point_name} "
        "и {destination_point_type} {destination_point_name}..."
    )


class Button(NamedTuple):
    NEW_SEARCH: str = "Новый поиск"
    MY_POINT_IS_NOT_HERE: str = "Нет моего пункта 😕"


class Word(NamedTuple):
    STATION = "станция"
    CITY = "город"


msg = Message()
btn = Button()
wrd = Word()
