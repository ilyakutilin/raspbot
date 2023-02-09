from http import HTTPStatus

import requests
from dotenv import load_dotenv

from . import exceptions as exc
from .logging import configure_logging

load_dotenv()

logger = configure_logging(__name__)


def get_response(
    endpoint: str, headers: dict[str, str | bytes | None]
) -> requests.Response:
    """Sends a request to the server and returns a response."""
    if headers["Authorization"] is None:
        raise exc.EmptyHeadersError(
            "Authorization key in the headers is missing."
        )
    try:
        logger.debug(f"Sending request to API endpoint {endpoint}.")
        response = requests.get(endpoint, headers)
        if response.status_code != HTTPStatus.OK:
            raise exc.APIStatusCodeError(
                f"Endpoint {endpoint} is unavailable - status: "
                f"{response.status_code} "
                f"{HTTPStatus(response.status_code).phrase}. "
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
        return response
