from raspbot.db.models import PointTypeEnum
from raspbot.db.routes.schema import PointResponse
from raspbot.services.shorteners.short_point import get_short_point_type

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

CLOSEST_DEPARTURES = "Ближайшие отправления:"
TODAY = "Сегодня:"
TOMORROW = "Завтра:"
ONLY_TOMORROW = "Ближайшие электрички только завтра:"
NO_CLOSEST_DEPARTURES = "В ближайшее время электричек по данному маршруту не будет 😕"
PRESS_DEPARTURE_BUTTON = (
    "Нажмите на кнопку со временем отправления под этим сообщением, "
    "чтобы посмотреть подробную информацию о рейсе, или выберите другую дату."
)
ERROR = "Произошла внутренняя ошибка приложения, приносим свои извинения."


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
