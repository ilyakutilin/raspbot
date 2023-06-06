from typing import NamedTuple

from raspbot.db.stations.schema import PointResponse


class SinglePointFound(PointResponse):
    is_departure: bool
    id: int | None = None
    yandex_code: str | None = None

    def __str__(self):
        dep_or_dest = "отправления" if self.is_departure else "назначения"
        type_ = "ст." if self.is_station else "г."
        title = self.title
        region = self.region_title
        return f"Пункт {dep_or_dest} - {type_} {title}, {region}"


class Message(NamedTuple):
    INPUT_DEPARTURE_POINT: str = "Введите пункт отправления (город или станцию):"
    POINT_NOT_FOUND: str = (
        "Не найдено такой станции или города. Попробуйте ввести по-другому:"
    )
    MISSING_POINT: str = "Попробуйте ввести название города или станции по-другому:"
    MULTIPLE_POINTS_FOUND: str = (
        "Было найдено несколько пунктов, удовлетворяющих вашему запросу.\n"
        "Выберите нужный пункт (город или станцию) из списка ниже:"
    )
    INPUT_DESTINATION_POINT: str = (
        "Теперь введите пункт назначения (город или станцию):"
    )
    SEARCHING_FOR_TIMETABLE: str = "Ищем раписание..."


class Button(NamedTuple):
    NEW_SEARCH: str = "Новый поиск"
    MY_POINT_IS_NOT_HERE: str = "Нет моего пункта 😕"


msg = Message()
btn = Button()
