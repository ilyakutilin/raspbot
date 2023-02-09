import json
from pathlib import Path
from typing import Mapping

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from raspbot.config import exceptions as exc
from raspbot.config.constants import FILES_DIR, HEADERS, STATIONS_LIST_ENDPOINT
from raspbot.config.logging import configure_logging
from raspbot.config.utils import get_response

load_dotenv()

initial_data_file = FILES_DIR / "stations.json"

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


def get_initial_data() -> Mapping:
    """
    Processes a JSON response with the initial data from API.

    Receives a JSON, returns a Python dictionary,
    JSON being received is about 40 MB in size with deep nesting.
    Sample of the JSON is this module's directory.
    """
    response: requests.Response = get_response(
        endpoint=STATIONS_LIST_ENDPOINT, headers=HEADERS
    )
    return response.json()


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
