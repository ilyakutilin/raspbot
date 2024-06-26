import datetime as dt
import locale

from raspbot.core.logging import configure_logging, log

logger = configure_logging(__name__)


@log(logger)
def _get_date_in_words(date: dt.date) -> str:
    """Converts the date object into word representation in Russian.

    Args:
        date (dt.date): The date that needs converting.

    Returns:
        str: The date in words.
    """
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
    week_day = date.strftime("%A").lower().replace("а", "у")
    word_date = date.strftime("%d %B %Y")
    return f"{week_day}, {word_date[0].replace('0', '') + word_date[1:]} "


@log(logger)
def prettify_day(date: dt.date) -> str:
    """Inserts the pretty description of the date into a message.

    Args:
        date (dt.date): The date that needs prettifying.

    Returns:
        str: The prettified date
    """
    word_date = _get_date_in_words(date=date)
    if date == dt.date.today() + dt.timedelta(1):
        return f"завтра, {word_date}"
    if date == dt.date.today() + dt.timedelta(2):
        return f"послезавтра, {word_date}"
    return word_date


@log(logger)
def prettify_time(seconds: int) -> str:
    """Inserts the pretty description of the time into a message."""
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes} minutes {remaining_seconds:.2f} seconds"
    hours = int(seconds // 3600)
    remaining_seconds = seconds % 3600
    minutes = int(remaining_seconds // 60)
    remaining_seconds = remaining_seconds % 60
    return f"{hours} hours {minutes:.2f} minutes {remaining_seconds:.2f} seconds"
