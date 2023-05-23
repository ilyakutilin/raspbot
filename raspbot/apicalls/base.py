from http import HTTPStatus

import aiohttp
from dotenv import load_dotenv

from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging

load_dotenv()

logger = configure_logging(__name__)


async def get_response(
    endpoint: str, headers: dict[str, str | bytes | None]
) -> dict | None:
    """Sends a request to the server and returns a response."""
    if headers["Authorization"] is None:
        raise exc.EmptyHeadersError("Authorization key in the headers is missing.")
    async with aiohttp.ClientSession() as session:
        try:
            logger.debug(f"Sending request to API endpoint {endpoint}.")
            response = await session.get(url=endpoint, headers=headers)
            if response.status != HTTPStatus.OK:
                raise exc.APIStatusCodeError(
                    f"Endpoint {endpoint} is unavailable - status: "
                    f"{response.status} "
                    f"{HTTPStatus(response.status).phrase}. "
                )
        except Exception as e:
            raise exc.APIConnectionError(
                f"An error occurred while connecting to endpoint {endpoint}. "
                f"Headers: {headers}. Error description: {e}"
            ) from e
        else:
            logger.debug(
                f"Request to API endpoint {endpoint} has been successfully "
                "completed and the response received."
            )
            return await response.json(content_type="text/html")
