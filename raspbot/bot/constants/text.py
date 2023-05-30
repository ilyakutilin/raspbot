from typing import NamedTuple


class Message(NamedTuple):
    GREETING: str = "Привет, {name}! 👋 \n\nЯ подскажу расписание электричек."
    INPUT_DEPARTURE_STATION: str = "Введите начальную станцию:"
    INPUT_DESTINATION_STATION: str = "Введите конечную станцию:"
    STATION_NOT_FOUND: str = "Такой станции не найдено. Попробуйте ввести по-другому."
    MULTIPLE_STATIONS_FOUND: str = (
        "Было найдено несколько станций, удовлетворяющих вашему запросу. "
        "Выберите нужную станцию из списка ниже:"
    )
    MY_STATION_IS_NOT_HERE: str = "Нет моей станции 😕"
    SEARCHING_FOR_TIMETABLE: str = (
        "Ищем раписание между станциями {departure_station} и {destination_station}..."
    )


class Button(NamedTuple):
    NEW_SEARCH: str = "Новый поиск"


msg = Message()
btn = Button()
