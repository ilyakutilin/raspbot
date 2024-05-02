import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from raspbot.apicalls.base import get_response
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.stations.schema import WorldPD
from raspbot.settings import settings

initial_data_file = settings.FILES_DIR / "stations.json"

logger = configure_logging(__name__)


def _save_initial_data_to_file(json_response: dict) -> Path:
    """Saves a JSON response in a file."""
    with open(initial_data_file, "w", encoding="utf8") as json_file:
        json.dump(json_response, json_file)
    return initial_data_file


def structure_initial_data(initial_data: dict | Path | Any) -> WorldPD | None:
    """Structures the initial data."""
    if isinstance(initial_data, Path):
        try:
            logger.debug("Starting to structure the initial data.")
            with open(file=initial_data, mode="r", encoding="UTF-8") as file:
                json_data = json.load(file)
            structured_data = WorldPD.model_validate(obj=json_data)
        except ValidationError as e:
            raise exc.DataStructureError(
                f"Pydantic data validation for the initial data failed: {e}."
            )
        else:
            logger.debug("Initial data has been structured.")
            return structured_data
    if isinstance(initial_data, dict):
        try:
            logger.debug("Starting to structure the initial data.")
            structured_data = WorldPD.model_validate(obj=initial_data)
        except ValidationError as e:
            raise exc.DataStructureError(
                f"Pydantic data validation for the initial data failed: {e}."
            )
        else:
            logger.debug("Initial data has been structured.")
            return structured_data
    logger.debug("Initial data not structured due to its incorrect format.")
    return None


if __name__ == "__main__":
    initial_data: dict = asyncio.run(
        get_response(endpoint=settings.STATIONS_LIST_ENDPOINT, headers=settings.headers)
    )
    _save_initial_data_to_file(initial_data)
    structure_initial_data(initial_data=initial_data_file)
