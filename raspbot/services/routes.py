from raspbot.core.exceptions import UserInputTooShortError
from raspbot.core.logging import configure_logging
from raspbot.db.stations.crud import CRUDSettlements, CRUDStations
from raspbot.db.stations.models import Settlement, Station
from raspbot.db.stations.schema import PointResponse

logger = configure_logging(name=__name__)

crud_stations = CRUDStations()
crud_settlements = CRUDSettlements()


class PointSelector:
    def __init__(self):
        self.choices: list[PointResponse] = []

    def _prettify(self, raw_user_input: str) -> str:
        return " ".join(raw_user_input.split()).lower()

    def validate_user_input(self, pretty_user_input: str):
        if len(pretty_user_input) < 2:
            raise UserInputTooShortError(
                f"User input {pretty_user_input} is too short."
            )

    def _sort_choices(self, pretty_user_input: str) -> list[PointResponse]:
        exact = []
        startwith = []
        contain = []
        for choice in self.choices:
            logger.info(f"Choice title: {choice.title}.")
            if choice.title.lower() == pretty_user_input:
                exact.append(choice)
                logger.info(f"Choice {choice.title} appended to exact.")
            elif choice.title.lower().startswith(pretty_user_input):
                startwith.append(choice)
                logger.info(f"Choice {choice.title} appended to startwith.")
            elif pretty_user_input in choice.title.lower():
                contain.append(choice)
                logger.info(f"Choice {choice.title} appended to contain.")
            else:
                logger.error(
                    f"Choice {choice.title} does not fall into any of the predefined "
                    "categories. Something needs to be done about that."
                )
            logger.info(
                f"Exact: {len(exact)}, startwith: {len(startwith)}, "
                f"contain: {len(contain)}, total: {len(exact + startwith + contain)}"
            )
        return exact + startwith + contain

    def _add_point_to_choices(
        self,
        points_from_db: list[Station | Settlement],
    ) -> None:
        for point_from_db in points_from_db:
            point = PointResponse(
                is_station=point_from_db.__class__.__name__ == "Station",
                id=point_from_db.id,
                title=point_from_db.title,
                yandex_code=point_from_db.yandex_code,
                region_title=point_from_db.region.title,
            )
            self.choices.append(point)

    async def _get_points_from_db(
        self,
        pretty_user_input: str,
    ) -> tuple[list[Settlement], list[Station]]:
        settlements_from_db: list[
            Settlement
        ] = await crud_settlements.get_settlements_by_title(title=pretty_user_input)
        stations_from_db: list[Station] = await crud_stations.get_stations_by_title(
            title=pretty_user_input
        )
        return settlements_from_db, stations_from_db

    async def select_points(self, raw_user_input: str) -> list[PointResponse] | None:
        pretty_user_input: str = self._prettify(raw_user_input=raw_user_input)
        settlements_from_db, stations_from_db = await self._get_points_from_db(
            pretty_user_input=pretty_user_input
        )
        if not settlements_from_db and not stations_from_db:
            return None
        if settlements_from_db:
            self._add_point_to_choices(points_from_db=settlements_from_db)
        if stations_from_db:
            self._add_point_to_choices(points_from_db=stations_from_db)
        logger.info(f"Кол-во пунктов: {len(self.choices)}")
        return self._sort_choices(pretty_user_input=pretty_user_input)


class PointRetriever:
    async def _get_point_from_db(
        self, point_id: int, is_station: bool
    ) -> Station | Settlement | None:
        if is_station:
            return await crud_stations.get_station_by_id(id=point_id)
        return await crud_settlements.get_settlement_by_id(id=point_id)

    async def get_point(self, point_id: int, is_station: bool) -> PointResponse:
        point_from_db: Station | Settlement = await self._get_point_from_db(
            point_id=point_id, is_station=is_station
        )
        point = PointResponse(
            is_station=is_station,
            id=point_id,
            title=point_from_db.title,
            yandex_code=point_from_db.yandex_code,
            region_title=point_from_db.region.title,
        )
        return point
