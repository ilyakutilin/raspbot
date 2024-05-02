from raspbot.core.exceptions import UserInputTooShortError
from raspbot.core.logging import configure_logging
from raspbot.db.models import PointORM, PointTypeEnum, RouteORM, UserORM
from raspbot.db.routes.crud import CRUDPoints, CRUDRoutes
from raspbot.db.routes.schema import PointResponse, RouteResponse
from raspbot.services.shorteners import get_short_point_type
from raspbot.services.users import add_or_update_recent

logger = configure_logging(name=__name__)

crud_points = CRUDPoints()
crud_routes = CRUDRoutes()


class PointSelector:
    """Point selection process."""

    def __init__(self):
        """Initializes PointSelector class instance."""
        self.choices: list[PointResponse] = []

    def _prettify(self, raw_user_input: str) -> str:
        return " ".join(raw_user_input.split()).lower()

    def _validate_user_input(self, pretty_user_input: str) -> bool:
        if len(pretty_user_input) < 2:
            raise UserInputTooShortError(
                f"User input {pretty_user_input} is too short."
            )
        if len(pretty_user_input) == 2:
            return True
        return False

    def _normalize_choice_title(self, choice_title: str) -> str:
        return choice_title.replace("Ё", "Е").replace("ё", "е").lower()

    def _sort_choices(self, pretty_user_input: str) -> list[PointResponse]:
        exact = []
        startwith = []
        contain = []
        for choice in self.choices:
            choice_title = self._normalize_choice_title(choice.title)
            logger.debug(f"Choice title: {choice.title}.")
            if choice_title == pretty_user_input:
                exact.append(choice)
                logger.debug(f"Choice {choice.title} appended to exact.")
            elif choice_title.startswith(pretty_user_input):
                startwith.append(choice)
                logger.debug(f"Choice {choice.title} appended to startwith.")
            elif pretty_user_input in choice_title:
                contain.append(choice)
                logger.debug(f"Choice {choice.title} appended to contain.")
            else:
                logger.error(
                    f"Choice {choice.title} does not fall into any of the predefined "
                    "categories. Something needs to be done about that."
                )
            logger.debug(
                f"Exact: {len(exact)}, startwith: {len(startwith)}, "
                f"contain: {len(contain)}, total: {len(exact + startwith + contain)}"
            )

        for choice_list in (exact, startwith, contain):

            def custom_sort_key(point: PointResponse):
                return point.point_type == PointTypeEnum.settlement

            choice_list.sort(key=custom_sort_key)

        return (exact + startwith + contain)[:50]

    def _split_choice_list(
        self, choice_list: list[PointResponse], chunk_size: int = 10
    ) -> list[list[PointResponse]]:
        resulting_list = []
        for i in range(0, len(choice_list), chunk_size):
            slice_stop = i + chunk_size
            resulting_list.append(choice_list[i:slice_stop])
        return resulting_list

    def _add_point_to_choices(self, points_from_db: list[PointORM]) -> None:
        for point_from_db in points_from_db:
            point = PointResponse(
                id=point_from_db.id,
                point_type=point_from_db.point_type,
                title=point_from_db.title,
                yandex_code=point_from_db.yandex_code,
                region_title=point_from_db.region.title,
            )
            self.choices.append(point)

    async def _get_points_from_db(self, pretty_user_input: str) -> list[PointORM]:
        strict_search: bool = self._validate_user_input(
            pretty_user_input=pretty_user_input
        )
        points_from_db: list[PointORM] = await crud_points.get_points_by_title(
            title=pretty_user_input, strict_search=strict_search
        )
        return points_from_db

    async def select_points(
        self, raw_user_input: str
    ) -> list[list[PointResponse]] | None:
        """Selects points."""
        pretty_user_input: str = self._prettify(raw_user_input=raw_user_input)
        points_from_db = await self._get_points_from_db(
            pretty_user_input=pretty_user_input,
        )
        if not points_from_db:
            return None
        self._add_point_to_choices(points_from_db=points_from_db)
        logger.info(f"Кол-во пунктов: {len(self.choices)}")
        sorted_choices: list[PointResponse] = self._sort_choices(
            pretty_user_input=pretty_user_input
        )
        return self._split_choice_list(choice_list=sorted_choices)


class PointRetriever:
    """Point retrieval process."""

    async def _get_point_from_db(self, point_id: int) -> PointORM | None:
        return await crud_points.get_point_by_id(id=point_id)

    async def get_point(self, point_id: int) -> PointResponse:
        """Get point from db by id."""
        point_from_db: PointORM = await self._get_point_from_db(point_id=point_id)
        point = PointResponse(
            id=point_from_db.id,
            point_type=point_from_db.point_type,
            title=point_from_db.title,
            yandex_code=point_from_db.yandex_code,
            region_title=point_from_db.region.title,
        )
        return point


class RouteFinder:
    """Route finding process."""

    async def get_or_create_route(
        self,
        departure_point: PointResponse,
        destination_point: PointResponse,
        user: UserORM,
    ) -> RouteResponse:
        """Gets route by departure and destination points or creates a new one."""
        route_from_db: RouteORM = await crud_routes.get_route_by_points(
            departure_point_id=departure_point.id,
            destination_point_id=destination_point.id,
        )
        dep_st_or_stl = get_short_point_type(point_type=departure_point.point_type)
        dest_st_or_stl = get_short_point_type(point_type=destination_point.point_type)
        if route_from_db:
            logger.info(
                f"Маршрут от {dep_st_or_stl} {departure_point.title} до "
                f"{dest_st_or_stl} {destination_point.title} уже существует."
            )
        else:
            logger.info(
                f"Маршрут от {dep_st_or_stl} {departure_point.title} до "
                f"{dest_st_or_stl} {destination_point.title} еще не существует."
                "Создаём новый маршрут."
            )
            instance = RouteORM(
                departure_point_id=departure_point.id,
                destination_point_id=destination_point.id,
            )
            route_from_db: RouteORM = await crud_routes.create(instance=instance)

        # Добавляем маршрут в последние у пользователя (либо обновляем дату)
        await add_or_update_recent(user_id=user.id, route_id=route_from_db.id)

        route = RouteResponse(
            id=route_from_db.id,
            departure_point=departure_point,
            destination_point=destination_point,
        )
        return route


class RouteRetriever:
    """Route retrieval process."""

    async def get_route_from_db(self, route_id: int) -> RouteORM | None:
        """Get route from db by id."""
        return await crud_routes.get_route_by_id(id=route_id)

    async def get_route_by_recent(self, recent_id: int) -> RouteORM | None:
        """Get route from db by recent id."""
        route: RouteORM = await crud_routes.get_or_none(_id=recent_id)
        return await crud_routes.get_route_by_id(id=route.id)
