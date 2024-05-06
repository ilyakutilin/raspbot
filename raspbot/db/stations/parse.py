import asyncio
import json
from pathlib import Path
from typing import Any, AsyncGenerator

from pydantic import ValidationError

from raspbot.apicalls.base import get_response
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.stations.schema import RegionPD
from raspbot.settings import settings

initial_data_file = settings.FILES_DIR / "stations.json"

logger = configure_logging(__name__)


def _save_initial_data_to_file(json_response: dict) -> Path:
    """Saves a JSON response in a file."""
    with open(initial_data_file, "w", encoding="utf8") as json_file:
        json.dump(json_response, json_file)
    return initial_data_file


def _get_initial_data_dict(initial_data: Path | Any) -> dict | None:
    """Returns the initial data as a dictionary."""
    if isinstance(initial_data, Path):
        with open(file=initial_data, mode="r", encoding="UTF-8") as file:
            json_data = json.load(file)
            return json_data

    return None


async def yield_regions(
    initial_data: dict | Path | Any,
) -> AsyncGenerator[RegionPD, None]:
    """Structures the initial data."""
    initial_data_dict = (
        _get_initial_data_dict(initial_data)
        if not isinstance(initial_data, dict)
        else initial_data
    )
    if not initial_data_dict:
        raise exc.DataStructureError("There is no initial data.")
    countries = initial_data_dict.get("countries")
    if not countries:
        raise exc.DataStructureError("There is no 'countries' key in the initial data.")
    for c in countries:
        regions = c.get("regions")
        if c.get("title") == "Россия" and isinstance(regions, list):
            for r in regions:
                try:
                    region_pd = RegionPD.model_validate(obj=r)
                except ValidationError as e:
                    region_title = r.get("title") or "Unknown Region"
                    raise exc.DataStructureError(
                        f"Pydantic data validation for region {region_title} failed: "
                        f"{e}."
                    )
                if region_pd.title:
                    yield region_pd


if __name__ == "__main__":
    initial_data: dict = asyncio.run(
        get_response(endpoint=settings.STATIONS_LIST_ENDPOINT, headers=settings.headers)
    )
    _save_initial_data_to_file(initial_data)

    async def main() -> None:
        """Obtains the initial data and populates the stations DB with it."""
        async for r in yield_regions(initial_data_file):
            print(r)

    asyncio.run(main())
