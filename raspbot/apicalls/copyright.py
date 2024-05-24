import asyncio
from typing import Mapping

from raspbot.apicalls.base import get_response
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging, log
from raspbot.settings import settings as s

logger = configure_logging(name=__name__)


@log(logger)
async def get_copyright() -> Mapping | None:
    """Gets the Yandex copyright."""
    url = s.COPYRIGHT_ENDPOINT
    headers = s.headers
    try:
        return await get_response(endpoint=url, headers=headers)
    except exc.APIError as e:
        logger.exception(e)
        return None


if __name__ == "__main__":
    copyright_ = asyncio.run(get_copyright())
    print(copyright_)
