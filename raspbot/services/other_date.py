import calendar as cal
import datetime as dt
import locale
import re

from dateutil import parser
from dateutil.relativedelta import relativedelta

from raspbot.bot.constants import messages as msg
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import RouteORM
from raspbot.db.routes.schema import RouteResponse
from raspbot.services.endings import days_with_ending
from raspbot.services.timetable import Timetable
from raspbot.settings import settings

logger = configure_logging(name=__name__)

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

SPECIFIC_WORDS = {
    "послезавтра": dt.date.today() + dt.timedelta(2),
    "завтра": dt.date.today() + dt.timedelta(1),
    "сегодня": dt.date.today(),
    "позавчера": msg.NO_TIMETABLE_IN_THE_PAST.format(
        date=(dt.date.today() - dt.timedelta(2)).strftime("%d %B %Y")
    ),
    "вчера": msg.NO_TIMETABLE_IN_THE_PAST.format(
        date=(dt.date.today() - dt.timedelta(1)).strftime("%d %B %Y")
    ),
}


MONTHS_IN_PREP_CASE = {
    1: "январе",
    2: "феврале",
    3: "марте",
    4: "апреле",
    5: "мае",
    6: "июне",
    7: "июле",
    8: "августе",
    9: "сентябре",
    10: "октябре",
    11: "ноябре",
    12: "декабре",
}


class CustomParserInfo(parser.parserinfo):
    """Base class for handling user inputs."""

    WEEKDAYS = [
        ("пн", "понедельник", "пон", "понед"),
        ("вт", "вторник", "втор", "вторн"),
        ("ср", "среда"),
        ("чт", "четверг", "чет", "четв"),
        ("пт", "пятница", "пят", "пятн"),
        ("сб", "суббота", "суб", "субб"),
        ("вс", "воскресенье", "вос", "воскр"),
    ]
    MONTHS = [
        ("янв", "января", "январь"),
        ("фев", "февраля", "февраль"),
        ("мар", "марта", "март"),
        ("апр", "апреля", "апрель"),
        ("май", "мая"),
        ("июн", "июня", "июнь"),
        ("июл", "июля", "июль"),
        ("авг", "августа", "август"),
        ("сен", "сентября", "сентябрь"),
        ("окт", "октября", "октябрь"),
        ("ноя", "ноября", "ноябрь"),
        ("дек", "декабря", "декабрь"),
    ]

    def __init__(self, *args, **kwargs):
        """Initialize CustomParserInfo object."""
        super().__init__(*args, **kwargs)


class CustomParserInfoDayFirst(CustomParserInfo):
    """Handling user inputs considering the day comes first."""

    def __init__(self, dayfirst=True, *args, **kwargs):
        """Initialize CustomParserInfoDayFirst object."""
        super().__init__(dayfirst=dayfirst, *args, **kwargs)
        self.dayfirst = dayfirst


class CustomParserInfoYearFirst(CustomParserInfo):
    """Handling user inputs considering the year comes first."""

    def __init__(self, yearfirst=True, *args, **kwargs):
        """Initialize CustomParserInfoYearFirst object."""
        super().__init__(yearfirst=yearfirst, *args, **kwargs)
        self.yearfirst = yearfirst


@log(logger)
def _check_specific_words(
    user_raw_date_input: str,
    specific_words: dict[str, dt.date | str] = SPECIFIC_WORDS,
) -> dt.date | None:
    """Checks if there is a specific word in user input and returns the date if so."""
    for key, value in specific_words.items():
        if key in user_raw_date_input:
            if isinstance(value, dt.date):
                return value
            if isinstance(value, str):
                raise exc.InvalidDateUserInputError(value)
            raise exc.InternalError(
                f"Unsupported value type: {type(value)}. Expected: dt.date or str."
            )

    return None


@log(logger)
def _number_is_a_valid_month_day(number: int) -> bool:
    """Checks if the number is a valid day in the month.

    If valid, return True.
    If not valid, raise InvalidDateUserInputError.
    """
    today = dt.date.today()
    days_in_month = cal.monthrange(today.year, today.month)[1]
    if number < 1:
        raise exc.InvalidDateUserInputError(
            msg.ZERO_OR_NEGATIVE.format(str(days_in_month))
        )
    if number > days_in_month:
        raise exc.InvalidDateUserInputError(
            msg.NO_SUCH_DAY_IN_MONTH.format(
                month=MONTHS_IN_PREP_CASE[today.month],
                days_with_ending=days_with_ending(days_in_month),
                days=days_in_month,
            )
        )
    return True


@log(logger)
def _check_number(user_raw_date_input: str) -> dt.date | None:
    """Checks if the user input is a number and returns the date if so."""
    user_date_input = user_raw_date_input.strip()
    try:
        number = int(user_date_input)
    except ValueError:
        return None

    _number_is_a_valid_month_day(number)

    today = dt.date.today()
    for n in range(1, 3):
        if number == (today - relativedelta(days=n)).day:
            raise exc.InvalidDateUserInputError(
                msg.NO_TIMETABLE_IN_THE_PAST.format(
                    date=(today - relativedelta(days=n)).strftime("%d %B %Y")
                )
            )
    try:
        parsed_date = parser.parse(timestr=user_date_input, dayfirst=True).date()
    except parser.ParserError as e:
        logger.error(f"{e.__class__.__name__.upper()}: {str(e)}")
        raise exc.InvalidDateUserInputError(msg.COULD_NOT_PARSE_DATE)

    if parsed_date < today:
        return today + relativedelta(months=1, day=today.day)
    return parsed_date


@log(logger)
def _replace_symbols_with_slashes(string: str) -> str:
    """Replaces any non-alphanumeric characters except spaces with slashes."""
    # Replace any non-alphanumeric characters except spaces with slashes
    # and remove leading and trailing slashes
    slashed_sorting = re.sub(r"[^\w\s]", "/", string.strip()).strip("/")
    # Remove repeating slashes
    return re.sub(r"/{2,}", "/", slashed_sorting)


@log(logger)
def _get_validated_date(
    dates: list[dt.date],
    max_days_into_past: int = settings.MAX_DAYS_INTO_PAST,
    max_months_into_future: int = settings.MAX_MONTHS_INTO_FUTURE,
) -> dt.date:
    """Validates the array of dates and returns the correct date or None."""
    today = dt.date.today()

    # Remove all dates in the past from the list of dates
    no_past = [r for r in dates if r >= today - relativedelta(days=max_days_into_past)]
    if not no_past:
        raise exc.InvalidDateUserInputError(
            msg.NO_TIMETABLE_IN_THE_PAST.format(date=dates[0].strftime("%d %B %Y"))
        )

    # Remove all dates more than X months in the future from the list of dates
    # filtered by the dates in the past
    no_future = [
        r for r in no_past if r <= today + relativedelta(months=max_months_into_future)
    ]
    if not no_future:
        raise exc.InvalidDateUserInputError(
            msg.TOO_FAR_INTO_FUTURE.format(
                date=no_past[0].strftime("%d %B %Y"),
                max_months_into_future=str(max_months_into_future),
            )
        )

    #

    if len(no_future) == 1:
        return no_future[0]

    # If there are two dates, return the one that is closest to today
    return no_future[0] if no_future[0] - today < no_future[1] - today else no_future[1]


@log(logger)
def _parse_date(date_string: str) -> dt.date | None:
    """Parses a date string into a datetime.date object."""
    results = []
    # Try two approaches to parse the date string: 1. DayFirst; 2. YearFirst
    for parser_obj in (CustomParserInfoDayFirst(), CustomParserInfoYearFirst()):
        try:
            results.append(
                parser.parse(timestr=date_string, parserinfo=parser_obj).date()
            )
        except parser.ParserError as e:
            logger.error(f"{e.__class__.__name__.upper()}: {str(e)}")

    if not results:
        raise exc.InvalidDateUserInputError(msg.COULD_NOT_PARSE_DATE)

    if len(results) > 2:
        error_text = "Length of the results list cannot be more than two."
        logger.error(error_text)
        raise exc.InternalError(error_text)

    # If there are two results, and the date string contains only one slash,
    # it means that the second result comes from YearFirst parser and it's very likely
    # that it is incorrect. For example: "5/6" must mean June 5th, not May 6th.
    if len(results) == 2 and date_string.count("/") == 1:
        results.pop(-1)

    return _get_validated_date(dates=results)


@log(logger)
def get_timetable_by_date(
    route: RouteORM | RouteResponse, user_raw_date_input: str
) -> Timetable:
    """Gets the timetable formatted message based on the user inputted date.

    Args:
        user_raw_date_input (str): User input from Telegram.

    Raises:
        exc.InvalidDateUserInputError: Raised if the date provided by the user
            is in an incorrect format.

    Returns:
        A Timetable object.
    """
    date = None
    check_funcs = (_check_specific_words, _check_number)
    for func in check_funcs:
        result = func(user_raw_date_input)
        if result:
            date = result
            break

    if not date:
        user_date_input = _replace_symbols_with_slashes(user_raw_date_input)
        date = _parse_date(user_date_input)

    if not date:
        raise exc.InvalidDateUserInputError(msg.COULD_NOT_PARSE_DATE)

    return Timetable(route=route, date=date)
