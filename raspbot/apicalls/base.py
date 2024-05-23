from http import HTTPStatus

import aiohttp
from dotenv import load_dotenv

from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging, log

load_dotenv()

logger = configure_logging(__name__)


@log(logger)
async def get_response(
    endpoint: str, headers: dict[str, str | bytes | None]
) -> dict | None:
    """
    Sends a request to the server and returns a response.

    Accepts:
        endpoint (string): The URL (endpoint) to send a request to;
        headers (dict): Headers (e.g. authentication token for an API).

    Raises:
        EmptyHeadersError: raised if there are no headers;
        APIStatusCodeError: raised in case of the bad status code;
        APIConnectionError: raised in case of connection errors.

    Returns:
        Dict or None: If the response is received as JSON, converts it to a dictionary;
        otherwise returns None.
    """
    if headers["Authorization"] is None:
        raise exc.EmptyHeadersError("No authorization key in the headers.")
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"Sending request to {endpoint}.")
            response = await session.get(url=endpoint, headers=headers)
            if response.status != HTTPStatus.OK:
                raise exc.APIStatusCodeError(
                    f"{endpoint} is unavailable - status: "
                    f"{response.status} "
                    f"{HTTPStatus(response.status).phrase}. "
                )
        except Exception as e:
            raise exc.APIConnectionError(
                f"Error connecting to {endpoint}. "
                f"Headers: {headers}. Error description: {e}"
            ) from e
        else:
            logger.info(f"Request to {endpoint} has been successul, response received.")
            return await response.json(content_type=None)
