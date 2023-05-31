from raspbot.core.logging import configure_logging
from raspbot.db.stations.crud import CRUDSettlements, CRUDStations
from raspbot.db.stations.models import Settlement, Station
from raspbot.db.stations.schema import PointResponse

logger = configure_logging(name=__name__)

crud_stations = CRUDStations()
crud_settlements = CRUDSettlements()


def _prettify(raw_user_input: str) -> str:
    return " ".join(raw_user_input.split())


def _add_point_to_choices(
    choices: list[PointResponse], points_from_db: list[Station | Settlement]
) -> None:
    for point_from_db in points_from_db:
        point = PointResponse(
            is_station=point_from_db.__class__.__name__ == "Station",
            title=point_from_db.title,
            yandex_code=point_from_db.yandex_code,
            region_title=point_from_db.region.title,
        )
        choices.append(point)


async def _get_points_from_db(
    pretty_user_input: str,
) -> tuple[list[Settlement], list[Station]]:
    settlements_from_db: list[
        Settlement
    ] = await crud_settlements.get_settlements_by_title(title=pretty_user_input)
    stations_from_db: list[Station] = await crud_stations.get_stations_by_title(
        title=pretty_user_input
    )
    return settlements_from_db, stations_from_db


async def select_points(raw_user_input: str) -> list[PointResponse] | None:
    pretty_user_input: str = _prettify(raw_user_input=raw_user_input)
    settlements_from_db, stations_from_db = await _get_points_from_db(
        pretty_user_input=pretty_user_input
    )
    if not settlements_from_db and not stations_from_db:
        return None
    choices: list[PointResponse] = []
    if settlements_from_db:
        _add_point_to_choices(choices=choices, points_from_db=settlements_from_db)
    if stations_from_db:
        _add_point_to_choices(choices=choices, points_from_db=stations_from_db)
    return choices
