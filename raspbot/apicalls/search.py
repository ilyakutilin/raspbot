import asyncio
import datetime as dt
import json
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Mapping

from raspbot.apicalls.base import get_response
from raspbot.core import exceptions as exc
from raspbot.core.email import send_email_async
from raspbot.core.logging import configure_logging, log
from raspbot.settings import settings as s

logger = configure_logging(name=__name__)


class Args(Enum):
    """Arguments for the main function search_between_stations."""

    @classmethod
    def list(cls):
        """Returns the list of arguments."""
        return list(map(lambda c: c.value, cls))


class Format(Args):
    """Format choices."""

    JSON = "json"
    XML = "xml"


class Lang(Args):
    """Language choices."""

    RU = "ru_RU"
    UA = "uk_UA"


class TransportTypes(Args):
    """Transport types choices."""

    PLANE = "plane"
    TRAIN = "train"
    SUBURBAN = "suburban"
    BUS = "bus"
    WATER = "water"
    HELICOPTER = "helicopter"


# Global API connectivity related variables
_exception_log: deque[dt.datetime] = deque(maxlen=s.API_EXCEPTION_THRESHOLD)
_last_exception_time = None


@log(logger)
def _check_exception_threshold(
    exception_threshold: int = s.API_EXCEPTION_THRESHOLD,
    exception_window: dt.timedelta = dt.timedelta(
        minutes=s.API_EXCEPTION_WINDOW_MINUTES
    ),
) -> None:
    """Checks the API exception threshold and raises exception if it's exceeded."""
    global _last_exception_time
    exception_window_minutes = exception_window.total_seconds() / 60
    if len(_exception_log) >= exception_threshold:
        _last_exception_time = _exception_log[-1]
        if dt.datetime.now() - _last_exception_time <= exception_window:
            raise exc.APIExceptionThresholdError(
                f"There were more than {exception_threshold} API errors in the last "
                f"{exception_window_minutes} minutes."
            )
    logger.debug(
        f"Number of API exceptions within the last {exception_window_minutes} minutes: "
        f"{len(_exception_log)}."
    )


@log(logger)
def _validate_arg(
    key: str,
    value: object,
) -> tuple[str, str]:
    """
    Validates the query component (arg of the main search_between_stations function).

    Accepts:
        - key (str): the name of the argument;
        - value (object): the value of the argument.

    Raises:
        - InvalidDateError: Date in the past. The search can only be today onwards.
        - InvalidValueError: The values format, lang, and transport_types
          must be selected from a preset list.
    """
    enums = {"format": Format, "lang": Lang, "transport_types": TransportTypes}
    if key == "date":
        if isinstance(value, dt.date) and value < dt.date.today():
            raise exc.DateInThePastError("Search date cannot be in the past.")
    if key in enums.keys() and not isinstance(value, Enum):
        allowed_values = enums[key].list()
        if value not in allowed_values:
            raise exc.InvalidValueError(
                f"Value for {key} can only be one of the following: {allowed_values}"
            )
    # Remove underscore from "from_" in key_str
    key_str = str(key).rstrip("_")
    value_str = str(value)
    logger.debug(f"{key_str=}, {value_str=}")
    return key_str, value_str


@log(logger)
def _generate_url(
    from_: str,
    to: str,
    date: dt.datetime | None = None,
    format: str | Format | None = None,
    lang: str | Lang | None = None,
    transport_types: str | TransportTypes | None = None,
    offset: int | None = None,
    limit: int | None = None,
    add_days_mask: bool | None = None,
    result_timezone: str | None = None,
    transfers: bool | None = None,
) -> str:
    """Generates the URL for the search_between_stations API call.

    Args:
        - from_ (str): Code of the departure point E.g. "s2000006".
        - to (str): Code of the destination point. E.g. "s9600721".
    Optional args:
        - date (dt.datetime): The date of the search.
          If None, API will default this to the general timetable for all dates.
        - format (str | Format): The format of the response.
          Can be either "json" or "xml". If None, API will
          default this to "json".
        - lang: (str | Lang), language code as per ISO 639: Russian "ru_RU"
          or Ukraininan "uk_UA". If None, API will default this to Russian.
        - transport_types: (str | TransportTypes): if None, API will
          search for all transport types.
        - offset: int: offset from trhe first search result.
          If None, API will default this to 0.
        - limit: int: max amount of results in response.
          If None, API will default this to 100.
        - add_days_mask: bool: whether a calendar will be shown for each thread.
          If None, API will default this to False.
        - result_timezone: str, timezone of the results. E.g. "Europe/Moscow".
          See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List,
          column "TZ identifier". If None, API will default this to the timezone
          of the corresponding point (station or settlement)
        - transfers: bool: whether to show transfer threads.
          If None, API will default this to False.

    Returns the string which is the URL for the search_between_stations API call.
    """
    # Get the local function variables, which at this stage are just the args passed
    # to it. We need to get them before we declare any other variables.
    args = locals().items()
    url_components = [f"{s.SEARCH_ENDPOINT}?"]
    logger.debug("Starting processing args.")
    for key, value in args:
        logger.debug(f"Arg {key}, value {value}.")
        if value is not None:
            logger.debug(f"Since value {value} is not None, starting its validation.")
            try:
                key_str, value_str = _validate_arg(key=key, value=value)
            except exc.InvalidDataError as e:
                logger.error(
                    f"Value '{value}' of arg '{key}' passed to search_between_stations "
                    f"is incorrect: {e}"
                )
                raise e
            logger.debug(
                f"URL at this stage: {''.join([item for item in url_components])}; "
                f"adding this: {key_str}={value_str}&"
            )
            url_components.append(f"{key_str}={value_str}&")
    url = "".join([item for item in url_components]).rstrip("&")
    logger.info(f"URL for search between points has been generated: {url}")
    return url


@log(logger)
async def _get_raw_timetable(
    url: str, headers: dict[str, str | bytes | None] = s.headers
) -> Mapping | None:
    """
    Search for the timetable between two points.

    Returns a dict with the timetable bewteen the points in raw format
    as received from the API.
    """
    try:
        response = await get_response(endpoint=url, headers=headers)
    except exc.APIError as e:
        logger.error(f"API Exception: {e}")
        _exception_log.append(dt.datetime.now())
        try:
            _check_exception_threshold()
        except exc.APIExceptionThresholdError as e:
            logger.error(f"API Exception Threshold has been exceeded: {e}")
            await send_email_async(e)
    return response


@log(logger)
async def search_between_stations(*args, **kwargs) -> Mapping | None:
    """
    Search for the timetable between two points.

    Returns a dict with the timetable bewteen the points in raw format
    as received from the API.
    """
    url = _generate_url(*args, **kwargs)
    return await _get_raw_timetable(url=url)


if __name__ == "__main__":
    tt = asyncio.run(
        search_between_stations(
            from_="s9601728", to="s2000006", date=dt.date.today(), offset=100
        )
    )
    tt_file = Path(s.FILES_DIR, "timetable.json")
    with open(file=tt_file, mode="w", encoding="UTF-8") as file:
        json.dump(obj=tt, fp=file, ensure_ascii=False, indent=2)
