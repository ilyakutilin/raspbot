import json
from pathlib import Path
from typing import Mapping

import aiohttp
from pydantic import BaseModel, ValidationError

from raspbot.apicalls.base import get_response
from raspbot.config import exceptions as exc
from raspbot.config.logging import configure_logging
from raspbot.settings import settings

initial_data_file = settings.FILES_DIR / "stations.json"

logger = configure_logging(__name__)


class Code(BaseModel):
    yandex_code: str | None = None
    esr_code: str | None = None


class Station(BaseModel):
    direction: str
    codes: Code
    station_type: str
    title: str
    longitude: float | str
    transport_type: str
    latitude: float | str


class Settlement(BaseModel):
    title: str
    codes: Code
    stations: list[Station]


class Region(BaseModel):
    settlements: list[Settlement]
    codes: Code
    title: str


class Country(BaseModel):
    regions: list[Region]
    codes: Code
    title: str


class World(BaseModel):
    countries: list[Country]


async def get_initial_data() -> Mapping:
    """
    Processes a JSON response with the initial data from API.

    Receives a JSON, returns a Python dictionary,
    JSON being received is about 40 MB in size with deep nesting.
    Sample of the JSON is this module's directory.
    """
    response: aiohttp.ClientResponse = await get_response(
        endpoint=settings.STATIONS_LIST_ENDPOINT, headers=settings.headers
    )
    return await response.json()


def _save_initial_data_to_file(json_response: dict) -> Path:
    """Saves a JSON response in a file."""
    with open(initial_data_file, "w", encoding="utf8") as json_file:
        json.dump(json_response, json_file)
    return initial_data_file


def structure_initial_data(initial_data: Mapping | Path) -> World | None:
    if isinstance(initial_data, Path):
        try:
            structured_data = World.parse_file(path=initial_data)
        except ValidationError as e:
            raise exc.DataStructureError(
                f"Pydantic data validation for the initial data failed: {e}."
            )
        else:
            return structured_data
    if isinstance(initial_data, Mapping):
        try:
            structured_data = World.parse_obj(obj=initial_data)
        except ValidationError as e:
            raise exc.DataStructureError(
                f"Pydantic data validation for the initial data failed: {e}."
            )
        else:
            return structured_data
    return None
