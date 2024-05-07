import datetime as dt

import raspbot.bot.constants.messages as msg
import raspbot.core.exceptions as exc
from raspbot.core.logging import configure_logging, log
from raspbot.db.routes.schema import ThreadResponsePD
from raspbot.services.timetable import Timetable

logger = configure_logging(name=__name__)


@log(logger)
def _remove_non_digits(user_raw_time_input: str) -> str:
    """Removes all the symbols except digits from the user input.

    Args:
        user_raw_time_input (str): User input from Telegram.

    Raises:
        exc.InvalidTimeUserInputError: Raised if the user input is too short and it
            won't be possible to deduce the time from such input.

    Returns:
        str: The string of digits from the user input.
    """
    if len(user_raw_time_input) < 3:
        raise exc.InvalidTimeUserInputError(msg.TIME_INPUT_TOO_SHORT)
    return "".join([d for d in user_raw_time_input if d.isdigit()])


@log(logger)
def _convert_to_time(user_raw_time_input: str) -> dt.time:
    """Converts the user input from string to datetime.time object.

    Args:
        user_raw_time_input (str): User input from Telegram.

    Raises:
        exc.InvalidTimeUserInputError: Raised if the user input is incorrect and it
            won't be possible to deduce the time from such input.

    Returns:
        datetime.time object.
    """
    user_digits = _remove_non_digits(user_raw_time_input=user_raw_time_input)
    if len(user_digits) > 4:
        raise exc.InvalidTimeUserInputError(msg.TIME_INPUT_TOO_LONG)

    try:
        hour = int(user_digits[:-2])
        minute = int(user_digits[-2:])
        return dt.time(hour=hour, minute=minute)
    except ValueError:
        raise exc.InvalidTimeUserInputError(msg.TIME_INPUT_NOT_RECOGNIZED)


@log(logger)
async def get_uid_by_time(user_raw_time_input: str, timetable_obj: Timetable) -> str:
    """Gets the depature UID based on the user inputted time.

    Args:
        user_raw_time_input (str): User input from Telegram.
        timetable_obj (Timetable): The Timetable object containing the timetable that
            needs to be searched for the time provided by the user above.

    Raises:
        exc.TimeNotFoundError: Raised if the time provided by the user is not found
            in the timetable.

    Returns:
        str: UID of the departure.
    """
    timetable = await timetable_obj.timetable
    logger.debug(f"{[dep.departure.strftime('%H:%M') for dep in timetable]}")
    dep_time: dt.time = _convert_to_time(user_raw_time_input=user_raw_time_input)
    logger.debug(f"Looking for: {dep_time}")
    try:
        departure: ThreadResponsePD = next(
            dep for dep in timetable if dep.departure.time() == dep_time
        )
    except StopIteration:
        user_time = dep_time.strftime("%H:%M")
        logger.error(f"User time {user_time} has not been found.")
        raise exc.TimeNotFoundError(msg.TIME_NOT_FOUND.format(time=user_time))
    return departure.uid
