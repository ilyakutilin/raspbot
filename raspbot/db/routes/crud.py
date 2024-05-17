from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from raspbot.core.logging import configure_logging
from raspbot.db.base import async_session_factory
from raspbot.db.crud import CRUDBase
from raspbot.db.models import PointORM, RouteORM

logger = configure_logging(__name__)


class CRUDPoints(CRUDBase):
    """CRUD for Point related operations."""

    def __init__(self, session: AsyncSession = async_session_factory()):
        """Initializes CRUDPoints class instance."""
        super().__init__(PointORM, session)

    async def get_points_by_title(
        self, title: str, strict_search: bool = False
    ) -> list[PointORM]:
        """Gets points by title."""
        search_template = "{title}" if strict_search else "%{title}%"

        async with self._session as session:
            fields_defining_uniqueness = [
                PointORM.title,
                PointORM.yandex_code,
                PointORM.point_type,
            ]
            # Define a subquery to find the maximum created_at
            # for each combination of title, yandex_code and point_type
            subquery = (
                select(
                    *fields_defining_uniqueness,
                    func.max(PointORM.created_at).label("max_created_at"),
                )
                .where(
                    func.unaccent(PointORM.title).ilike(
                        search_template.format(title=title)
                    )
                )
                .group_by(*fields_defining_uniqueness)
                .alias("subq")
            )

            # Define the main query to select the PointORM instances
            # with the latest created_at for each group
            query = (
                select(PointORM)
                .join(
                    subquery,
                    and_(
                        PointORM.title == subquery.c.title,
                        PointORM.yandex_code == subquery.c.yandex_code,
                        PointORM.point_type == subquery.c.point_type,
                    ),
                )
                .where(PointORM.created_at == subquery.c.max_created_at)
                .options(joinedload(PointORM.region))
                .order_by(PointORM.title)
                .limit(30)
            )
            points = await session.execute(query)
            return points.scalars().unique().all()

    async def get_point_by_id(self, id: int) -> PointORM:
        """Gets point by ID."""
        async with self._session as session:
            point = await session.execute(
                select(PointORM)
                .options(joinedload(PointORM.region))
                .where(PointORM.id == id)
            )
            return point.scalars().first()


class CRUDRoutes(CRUDBase):
    """CRUD for Route related operations."""

    def __init__(self, session: AsyncSession = async_session_factory()):
        """Initializes CRUDRoutes class instance."""
        super().__init__(RouteORM, session)

    async def get_route_by_points(
        self, departure_point_id: int, destination_point_id: int
    ) -> RouteORM:
        """Gets route by departure and destination point IDs."""
        async with self._session as session:
            route = await session.execute(
                select(RouteORM).where(
                    and_(
                        RouteORM.departure_point_id == departure_point_id,
                        RouteORM.destination_point_id == destination_point_id,
                    )
                )
            )
            return route.scalars().first()

    async def get_route_by_id(self, id: int) -> RouteORM:
        """Gets route by ID."""
        async with self._session as session:
            route = await session.execute(
                select(RouteORM)
                .options(
                    joinedload(RouteORM.departure_point),
                    joinedload(RouteORM.destination_point),
                )
                .where(RouteORM.id == id)
            )
            return route.scalars().first()
