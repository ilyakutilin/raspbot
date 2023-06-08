from typing import NamedTuple

from raspbot.db.stations.schema import PointResponse


class SinglePointFound:
    def __init__(self, point: PointResponse, is_departure: bool):
        self.is_departure: bool = is_departure
        self.is_station: bool = point.is_station
        self.title: str = point.title
        self.region_title: str = point.region_title

    def __str__(self):
        dep_or_dest = "отправления" if self.is_departure else "назначения"
        type_ = "ст." if self.is_station else "г."
        title = self.title
        region = self.region_title
        return f"Пункт {dep_or_dest} - {type_} {title}, {region}."


class Message(NamedTuple):
    INPUT_DEPARTURE_POINT: str = "Введите пункт отправления (город или станцию):"
    INPUT_TOO_SHORT: str = "Для поиска необходимо ввести как минимум два смивола."
    POINT_NOT_FOUND: str = (
        "Не найдено такой станции или города. Попробуйте ввести по-другому."
    )
    MISSING_POINT: str = (
        "Жаль, что ничего не нашлось. "
        "Попробуйте ввести название города или станции по-другому."
    )
    WHAT_YOU_WERE_LOOKING_FOR: str = "Это то, что вы искали?"
    MULTIPLE_POINTS_FOUND: str = (
        "Было найдено несколько пунктов, удовлетворяющих вашему запросу.\n"
        "Выберите нужный пункт (город или станцию) из списка ниже, если он есть. "
        'Если нужного вам пункта нет - нажмите кнопку "Нет моего пункта"'
    )
    INPUT_DESTINATION_POINT: str = (
        "Теперь введите пункт назначения (город или станцию):"
    )
    SEARCHING_FOR_TIMETABLE: str = "Ищем раписание..."


class Button(NamedTuple):
    NEW_SEARCH: str = "Новый поиск"
    CONFIRM_SINGE_POINT: str = "Да, это то, что я искал 👍"
    DECLINE_SINGLE_POINT: str = "Нет, это не то, что мне нужно 🙁"
    MY_POINT_IS_NOT_HERE: str = "Нет моего пункта 😕"


msg = Message()
btn = Button()
