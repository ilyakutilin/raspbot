import time

from raspbot.db.models import PointTypeEnum
from raspbot.db.routes.schema import PointResponse, ThreadResponse
from raspbot.services.shorteners.short_point import get_short_point_type
from raspbot.settings import settings

# START

GREETING_NEW_USER = (
    "Здравствуйте, {first_name}! ✋\n\nВы раньше у нас не были, поэтому вам доступна "
    "только функция нового поиска. Для этого нажмите <b>/search</b> и следуйте "
    "указаниям."
)
GREETING_EXISTING_USER = (
    "Здравствуйте, {first_name}! ✋\n\n<b>/search</b> - Новый поиск\n"
    "<b>/recent</b> - Ваши недавние маршруты\n<b>/fav</b> - Ваше избранное"
)


# ROUTES


class SinglePointFound:
    def __init__(self, point: PointResponse, is_departure: bool):
        self.is_departure: bool = is_departure
        self.point_type: PointTypeEnum = point.point_type
        self.title: str = point.title
        self.region_title: str = point.region_title

    def __str__(self):
        dep_or_dest = "отправления" if self.is_departure else "назначения"
        type_ = get_short_point_type(self.point_type)
        title = self.title
        region = self.region_title
        return f"Пункт {dep_or_dest} - {type_} {title}, {region}."


INPUT_DEPARTURE_POINT = "Введите пункт отправления (город или станцию):"
INPUT_TOO_SHORT = "Для поиска необходимо ввести как минимум два символа."
POINT_NOT_FOUND = "Не найдено такой станции или города. Попробуйте ввести по-другому."
MISSING_POINT = (
    "Жаль, что ничего не нашлось 😢\n"
    "Попробуйте ввести название города или станции по-другому."
)
WHAT_YOU_WERE_LOOKING_FOR = "Это то, что вы искали?"
MULTIPLE_POINTS_FOUND = (
    "Было найдено несколько пунктов, удовлетворяющих вашему запросу.\n"
    "Выберите нужный пункт (город или станцию) из списка ниже, если он есть. "
    'Если нужного вам пункта нет - нажмите кнопку "Нет моего пункта"'
)
MORE_POINT_CHOICES = "Вот ещё варианты:"
INPUT_DESTINATION_POINT = "Теперь введите пункт назначения (город или станцию):"


# TIMETABLE

CLOSEST_DEPARTURES = "Вот ближайшие отправления по маршруту {route}."
ROUTE_IN_BRACKETS = (
    "В скобках рядом с каждым отправлением указан маршрут электрички "
    "(ее начальный и конечный пункт) для информации."
)
DEPARTURE_STATION_IN_BRACKETS = (
    "В скобках рядом с каждым отправлением указана станция отправления."
)
DESTINATION_STATION_IN_BRACKETS = (
    "В скобках рядом с каждым отправлением указана станция назначения."
)
STATIONS_IN_BRACKETS = (
    "В скобках рядом с каждым отправлением указаны станции отправления и назначения."
)
NO_CLOSEST_DEPARTURES = (
    "Сегодня электричек по маршруту {route} не будет 😕\n\n"
    'Можно поискать на завтра. Для этого нажмите на кнопку "Завтра" под этим '
    "сообщением."
)
PRESS_DEPARTURE_BUTTON = (
    "Нажмите на кнопку со временем отправления под этим сообщением, "
    "чтобы посмотреть подробную информацию о рейсе, или выберите другую дату."
)
SAME_DEPARTURE = "Вы выбрали тот же самый рейс"
ERROR = "Произошла внутренняя ошибка приложения, приносим свои извинения."


class FormattedUnifiedThreadList:
    def __init__(self, thread_list: list[ThreadResponse]):
        self.thread_list = thread_list
        self.simple_threads = "\n".join([dep.message_with_route for dep in thread_list])

    def station_to_settlement(self) -> str:
        return (
            f"Все электрички прибывают на станцию {self.thread_list[0].to}."
            f"\n{ROUTE_IN_BRACKETS}\n\n{self.simple_threads}"
        )

    def settlement_to_station(self) -> str:
        return (
            f"Все электрички отправляются от станции {self.thread_list[0].from_}."
            f"\n{ROUTE_IN_BRACKETS}\n\n{self.simple_threads}"
        )

    def settlement_to_settlement(self) -> str:
        return (
            f"Все электрички отправляются от станции {self.thread_list[0].from_} "
            f"и прибывают на станцию {self.thread_list[0].to}."
            f"\n{ROUTE_IN_BRACKETS}\n\n{self.simple_threads}"
        )


class FormattedDifferentThreadList:
    def __init__(self, thread_list: list[ThreadResponse]):
        self.thread_list = thread_list

    def station_to_settlement(self) -> str:
        return (
            "⚠️ Обратите внимание, что электрички прибывают на разные станции!\n"
            "В скобках рядом с каждым отправлением указана станция прибытия.\n\n"
        ) + "\n".join(dep.message_with_destination_station for dep in self.thread_list)

    def settlement_to_station(self) -> str:
        return (
            "⚠️ Обратите внимание, что электрички отправляются с разных станций!\n"
            "В скобках рядом с каждым отправлением указана станция отправления.\n\n"
        ) + "\n".join(dep.message_with_departure_station for dep in self.thread_list)

    def settlement_one_to_settlement_diff(self) -> str:
        return (
            f"Все электрички отправляются от станции {self.thread_list[0].from_}.\n"
            "⚠️ Однако обратите внимание, что станции прибытия у всех электричек "
            "разные!\nОни указаны в скобках рядом с каждым отправлением.\n\n"
        ) + "\n".join(dep.message_with_destination_station for dep in self.thread_list)

    def settlement_diff_to_settlement_one(self) -> str:
        return (
            "⚠️ Обратите внимание, что у всех электричек разные станции отправления!\n"
            "Они указаны в скобках рядом с каждым отправлением.\n"
            f"Станция прибытия всех электричек - {self.thread_list[0].to}.\n\n"
        ) + "\n".join(dep.message_with_departure_station for dep in self.thread_list)

    def settlement_diff_to_settlement_diff(self) -> str:
        return (
            "⚠️ Обратите внимание, что у всех электричек разные станции отправления "
            "и прибытия!\nОни указаны в скобках рядом с каждым отправлением.\n\n"
        ) + "\n".join(
            dep.message_with_departure_and_destination for dep in self.thread_list
        )


class ThreadInfo:
    def __init__(self, thread: ThreadResponse):
        self.thread = thread

    def __str__(self):
        express = ", " + self.thread.express_type if self.thread.express_type else ""
        dep_platform = (
            ", " + self.thread.departure_platform
            if self.thread.departure_platform
            else ""
        )
        dep_terminal = (
            ", " + self.thread.departure_terminal
            if self.thread.departure_terminal
            else ""
        )
        dest_platform = (
            ", " + self.thread.arrival_platform if self.thread.arrival_platform else ""
        )
        dest_terminal = (
            ", " + self.thread.arrival_terminal if self.thread.arrival_terminal else ""
        )
        duration = time.strftime("%H ч. %M мин.", time.gmtime(self.thread.duration))
        return (
            f"<b>№ поезда:</b> {self.thread.number}\n"
            f"<b>Тип поезда:</b> {self.thread.transport_subtype}{express}\n"
            f"<b>Маршрут поезда:</b> {self.thread.title}\n"
            f"<b>Перевозчик:</b> {self.thread.carrier}\n"
            f"<b>Отправление от ст. {self.thread.from_}:</b> "
            f"{self.thread.str_time}{dep_platform}{dep_terminal}\n"
            f"<b>Прибытие на ст. {self.thread.to}:</b> "
            f"{self.thread.arrival.strftime(settings.DEP_FORMAT)}"
            f"{dest_platform}{dest_terminal}\n"
            f"<b>Останавливается:</b> {self.thread.stops}\n"
            f"<b>Время в пути:</b> {duration}\n"
            # TODO: Ticket prices
            f"<b>Стоимость билета:</b> {self.thread.ticket_price} руб.\n"
        )


# USERS

NO_RECENT = (
    "Вы еще не искали раписания, поэтому список недавних маршрутов пуст 🤷‍♂️\n\n"
    "Нажмите <b>/search</b>, чтобы начать новый поиск\n🚃🚃🚃🚃🚃🚃"
)
NO_FAV_NO_RECENT = (
    "Вы пока не добавляли маршруты в избранное 🤷‍♂️\n\n"
    "Нажмите <b>/search</b>, чтобы начать новый поиск\n🚃🚃🚃🚃🚃🚃\n"
    "После вывода результатов поиска по маршруту внизу будет кнопка для добавления "
    "его в избранное ⭐️"
)
NO_FAV_YES_RECENT = (
    "Вы пока не добавляли маршруты в избранное 🤷‍♂️\n\n"
    "Но у вас есть недавние маршруты, по которым вы искали расписания 🕑\n"
    "Вы можете нажать на маршрут, который вы хотите добавить в избранное, "
    'или добавить их все сразу, нажав на кнопку "Добавить все".\n\n'
    "Также вы можете нажать на <b>/search</b>, чтобы начать новый поиск\n🚃🚃🚃🚃🚃🚃"
    "После вывода результатов поиска по маршруту внизу будет кнопка для добавления "
    "его в избранное ⭐️"
)
RECENT_LIST = (
    "Вот список маршрутов, расписания по которым вы недавно искали. "
    "Нажмите на нужный маршрут, чтобы открыть расписание."
)
FAV_LIST = (
    "Вот список маршрутов, добавленных вами в избранное. "
    "Нажмите на нужный маршрут, чтобы открыть расписание."
)
ROUTE_ADDED_TO_FAV = "Маршрут {route} добавлен в избранное 👍"


class MultipleToFav:
    def __init__(self, amount: int):
        self.amount: int = amount

    def _words_with_endings(self):
        x = str(self.amount)
        if x == "1" or self.amount > 20 and x[-1] == "1":
            return f"{x} маршрут был добавлен"
        if x[-1] in ["2", "3", "4"]:
            return f"{x} маршрута было добавлено"
        return f"{x} маршрутов было добавлено"

    def __str__(self):
        return f"{self._words_with_endings()} в избранное 👍"
