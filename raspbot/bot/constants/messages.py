import time
from abc import ABC, abstractmethod

from raspbot.db.models import PointTypeEnum
from raspbot.db.routes.schema import PointResponse, ThreadResponse
from raspbot.services.shorteners.short_point import get_short_point_type
from raspbot.services.split import split_string_list
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
    """Message displayed when a single point was found while searching."""

    def __init__(self, point: PointResponse, is_departure: bool):
        """Initializes the SinglePointFound class instance."""
        self.is_departure: bool = is_departure
        self.point_type: PointTypeEnum = point.point_type
        self.title: str = point.title
        self.region_title: str = point.region_title

    def __str__(self):
        """Returns the string representation of the class instance."""
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
TODAY_DEPARTURES = (
    "Вот отправления по маршруту {route} с текущего момента до конца дня."
)
DATE_DEPARTURES = "Вот отправления по маршруту {route} на {date}."
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
NO_TODAY_DEPARTURES = (
    "Сегодня электричек по маршруту {route} не будет 😕\n\n"
    'Можно поискать на завтра. Для этого нажмите на кнопку "Завтра" под этим '
    "сообщением."
)
PRESS_DEPARTURE_BUTTON = (
    "Нажмите на кнопку со временем отправления под этим сообщением, "
    "чтобы посмотреть подробную информацию о рейсе, или выберите другую дату."
)
PRESS_DEPARTURE_BUTTON_OR_TYPE = (
    "Чтобы посмотреть подробную информацию о рейсе, нажмите на кнопку со временем "
    "отправления под этим сообщением. В кнопки выведены только ближайшие отправления. "
    "Если вас интересуют другие рейсы, просто отправьте сообщение со временем "
    "отправления в любом формате, например:\n05:25 или 5.25 или 525"
)
TYPE_DEPARTURE = (
    "Чтобы посмотреть подробную информацию о рейсе, отправьте сообщение со временем "
    "отправления в любом формате, например:\n05:25 или 5.25 или 525"
)
SAME_DEPARTURE = "Вы выбрали тот же самый рейс"
CONT_NEXT_MSG = "Продолжение в следующем сообщении."
TYPE_ARBITRARY_DATE = (
    "Пожалуйста, отправьте сообщение с желаемой датой.\n\n"
    "<b>Примеры:</b>\n"
    '"<b>послезавтра</b>"\n"<b>суббота</b>" или "<b>сб</b>"\n'
    '"<b>25</b>" (число текущего месяца, или следующего, если в этом месяце '
    "такое число уже было)\n"
    '"<b>25.04.2024</b>" или "<b>25.4.24</b>" или "<b>25.4</b>"'
)
ERROR = "Произошла внутренняя ошибка приложения, приносим свои извинения."


class FormattedThreadList(ABC):
    """Base abstract class for formatting a list of threads."""

    def __init__(
        self,
        thread_list: list[ThreadResponse],
        max_length: int = settings.MAX_TG_MSG_LENGTH,
    ):
        """Initializes the FormattedThreadList class instance."""
        self.thread_list = thread_list
        self.max_length = max_length

    def __len__(self):
        """Returns the length of the list which is the number of timetable threads."""
        return len(self.thread_list)

    def _split_threads(self, basic_msg: str, threads: list[str]) -> tuple[str]:
        split_at = self.max_length - len(basic_msg)
        split_thread_lists: list[list[str]] = split_string_list(
            string_list=threads, limit=split_at
        )
        for tl in split_thread_lists:
            split_thread_lists[split_thread_lists.index(tl)] = "\n".join(
                dep for dep in tl
            )
        return tuple(split_thread_lists)

    @abstractmethod
    def station_to_settlement(self) -> str:
        """Abstract method for the station-to-settlement case."""
        raise NotImplementedError("Please implement station_to_settlement.")

    @abstractmethod
    def settlement_to_station(self) -> str:
        """Abstract method for the settlement_to_station case."""
        raise NotImplementedError("Please implement settlement_to_station.")


class FormattedUnifiedThreadList(FormattedThreadList):
    """Class for formatting threads with the same departure and the same destination."""

    @property
    def _simple_threads(self) -> str:
        return "\n".join([dep.message_with_route for dep in self.thread_list])

    def station_to_settlement(self) -> str:
        """Returns the formatted message(s) for the station-to-settlement case.

        Departure point is a station, but the destination point is a settlement,
        thus a destination station shall be clearly defined in a message.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=(
                f"Все электрички прибывают на станцию {self.thread_list[0].to}."
                f"\n{ROUTE_IN_BRACKETS}\n\n"
            ),
            threads=self._simple_threads,
        )

    def settlement_to_station(self) -> str:
        """Returns the formatted message(s) for the settlement_to_station case.

        Departure point is a settlement, but the destination point is a station,
        thus a departure station shall be clearly defined in a message.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=(
                f"Все электрички отправляются от станции {self.thread_list[0].from_}."
                f"\n{ROUTE_IN_BRACKETS}\n\n"
            ),
            threads=self._simple_threads,
        )

    def settlement_to_settlement(self) -> str:
        """Returns the formatted message(s) for the settlement_to_settlement case.

        Both the departure and the destination points are settlements, thus both the
        departure and the destination stations shall be clearly defined in a message.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=(
                f"Все электрички отправляются от станции {self.thread_list[0].from_} "
                f"и прибывают на станцию {self.thread_list[0].to}."
                f"\n{ROUTE_IN_BRACKETS}\n\n"
            ),
            threads=self._simple_threads,
        )


class FormattedDifferentThreadList(FormattedThreadList):
    """Class for formatting threads with different departures and/or destinations."""

    @property
    def _different_destination_stations(self) -> str:
        return (
            "⚠️ Обратите внимание, что электрички прибывают на разные станции!\n"
            "В скобках рядом с каждым отправлением указана станция прибытия.\n\n"
        )

    @property
    def _different_departure_stations(self) -> str:
        return (
            "⚠️ Обратите внимание, что электрички отправляются с разных станций!\n"
            "В скобках рядом с каждым отправлением указана станция отправления.\n\n"
        )

    @property
    def _same_dep_diff_dest_stations(self) -> str:
        return (
            f"Все электрички отправляются от станции {self.thread_list[0].from_}.\n"
            "⚠️ Однако обратите внимание, что станции прибытия у всех электричек "
            "разные!\nОни указаны в скобках рядом с каждым отправлением.\n\n"
        )

    @property
    def _diff_dep_same_dest_stations(self) -> str:
        return (
            "⚠️ Обратите внимание, что у всех электричек разные станции отправления!\n"
            "Они указаны в скобках рядом с каждым отправлением.\n"
            f"Станция прибытия всех электричек - {self.thread_list[0].to}.\n\n"
        )

    @property
    def _diff_dep_diff_dest_stations(self) -> str:
        return (
            "⚠️ Обратите внимание, что у всех электричек разные станции отправления "
            "и прибытия!\nОни указаны в скобках рядом с каждым отправлением.\n\n"
        )

    def station_to_settlement(self) -> tuple[str]:
        """Returns the formatted message(s) for the station-to-settlement case.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=self._different_destination_stations,
            threads=[dep.message_with_destination_station for dep in self.thread_list],
        )

    def settlement_to_station(self) -> tuple[str]:
        """Returns the formatted message(s) for the settlement_to_station case.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=self._different_departure_stations,
            threads=[dep.message_with_departure_station for dep in self.thread_list],
        )

    def settlement_one_to_settlement_diff(self) -> tuple[str]:
        """Returns the formatted message(s) for settlement_one_to_settlement_diff case.

        The same departure station within a given settlement, but different
        destination stations.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=self._same_dep_diff_dest_stations,
            threads=[dep.message_with_destination_station for dep in self.thread_list],
        )

    def settlement_diff_to_settlement_one(self) -> tuple[str]:
        """Returns the formatted message(s) for settlement_diff_to_settlement_one case.

        Different departure stations within a given settlement, but the same
        destination station.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=self._diff_dep_same_dest_stations,
            threads=[dep.message_with_departure_station for dep in self.thread_list],
        )

    def settlement_diff_to_settlement_diff(self) -> tuple[str]:
        """Returns the formatted message(s) for settlement_diff_to_settlement_diff case.

        Different departure stations within a given settlement, as well as different
        destination stations.

        The message is split into multiple ones if they are too long.
        The return format is a tuple. If a message length is below the max limit
        of the Telegram API, then the tuple contains a single string.
        """
        return self._split_threads(
            basic_msg=self._diff_dep_diff_dest_stations,
            threads=[
                dep.message_with_departure_and_destination for dep in self.thread_list
            ],
        )


class ThreadInfo:
    """Information about a particular timetable thread."""

    def __init__(self, thread: ThreadResponse):
        """Initialize the ThreadInfo class instance."""
        self.thread = thread

    def __str__(self):
        """Returns the string representation of the class instance."""
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
    """Class for multiple routes to be added to the favourite list."""

    def __init__(self, amount: int):
        """Initializes the MultipleToFav class instance."""
        self.amount: int = amount

    def _words_with_endings(self):
        x = str(self.amount)
        if x == "1" or self.amount > 20 and x[-1] == "1":
            return f"{x} маршрут был добавлен"
        if x[-1] in ["2", "3", "4"]:
            return f"{x} маршрута было добавлено"
        return f"{x} маршрутов было добавлено"

    def __str__(self):
        """Returns the string representation of the class instance."""
        return f"{self._words_with_endings()} в избранное 👍"


# ERRORS

TIME_INPUT_TOO_SHORT = (
    "Не получилось понять, что за отправление вы имеете в виду.\n"
    "Нужно ввести хотя бы три цифры - минимум одну для часов, и две для минут. Между "
    "часами и минутами можно поставить любой знак или не ставить никаких знаков "
    "вообще, но три цифры должно присутствовать 🙂"
)

TIME_INPUT_TOO_LONG = (
    "Не получилось понять, что за отправление вы имеете в виду.\n"
    "Введите максимум четыре цифры - две для часов и две для минут. Между "
    "часами и минутами можно поставить любой знак или не ставить никаких знаков "
    "вообще, но больше четырех цифр вводить не нужно 🙂"
)

TIME_INPUT_NOT_RECOGNIZED = (
    "Не получилось понять, что за отправление вы имеете в виду.\n"
    "Вот пример ввода времени отправления: 1525. Так будет понятно, что 15 - это часы, "
    "а 25 - это минуты."
)

TIME_NOT_FOUND = (
    "Вы искали {time}, но такого времени отправления нет 😕\n"
    "Проверьте, пожалуйста, возможно, где-то закралась опечатка 👀"
)
