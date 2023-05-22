import asyncio
import datetime
from typing import Mapping

from raspbot.apicalls.base import get_response
from raspbot.core.exceptions import InvalidValueError
from raspbot.core.logging import configure_logging
from raspbot.settings import settings as s

logger = configure_logging(name=__name__)


def _is_valid(value: object, key_name: str, allowed_values: set) -> bool:
    if value not in allowed_values:
        raise InvalidValueError(
            f"The {key_name} value shall be one of the following: {allowed_values}"
        )
    return value in allowed_values


async def search_between_stations(from_: str, to: str, **kwargs) -> Mapping:
    url_components = [f"{s.SEARCH_ENDPOINT}?from={from_}&to={to}"]
    optional_keys = {
        "format",
        "lang",
        "date",
        "transport_types",
        "offset",
        "limit",
        "add_days_mask",
        "result_timezone",
        "transfers",
    }
    allowed_values = {
        "format": {"json", "xml"},
        "lang": {"ru_RU", "uk_UA"},
        "transport_types": {"plane", "train", "suburban", "bus", "water", "helicopter"},
    }
    for key, value in kwargs.items():
        if key in allowed_values:
            _is_valid(value=value, key_name=key, allowed_values=allowed_values[key])
        if key in optional_keys:
            url_components.append(f"&{key}={value}")
    url = "".join([str(item) for item in url_components])
    logger.info(f"Search between stations URL is {url}")
    response = await get_response(endpoint=url, headers=s.headers)
    return await response.json()


if __name__ == "__main__":
    asyncio.run(
        search_between_stations(
            from_="s9600692", to="s9601805", date=datetime.date(2023, 5, 18)
        )
    )
