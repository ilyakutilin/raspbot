from typing import Generator

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from raspbot.apicalls.search import TransportTypes
from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.models import CountryORM, PointORM, RouteORM


class CRUDPoints(CRUDBase):
    """CRUD for Point related operations."""

    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        """Initializes CRUDPoints class instance."""
        super().__init__(PointORM, sessionmaker)

    async def get_points_by_title(
        self, title: str, strict_search: bool = False
    ) -> list[PointORM]:
        """Gets points by title."""
        search_template = "{title}" if strict_search else "%{title}%"
        async with self._sessionmaker() as session:
            points = await session.execute(
                select(PointORM)
                .options(selectinload(PointORM.region))
                .join(CountryORM)
                .where(
                    func.unaccent(PointORM.title).ilike(
                        search_template.format(title=title)
                    )
                )
                .where(CountryORM.title == "Россия")
                .where(
                    or_(
                        PointORM.transport_type == TransportTypes.TRAIN.value,
                        PointORM.transport_type.is_(None),
                    )
                )
                .order_by(PointORM.title)
                .limit(30)
            )
            return points.scalars().unique().all()

    async def get_point_by_id(self, id: int) -> PointORM:
        """Gets point by ID."""
        async with self._sessionmaker() as session:
            point = await session.execute(
                select(PointORM)
                .options(selectinload(PointORM.region))
                .where(PointORM.id == id)
            )
            return point.scalars().first()


class CRUDRoutes(CRUDBase):
    """CRUD for Route related operations."""

    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        """Initializes CRUDRoutes class instance."""
        super().__init__(RouteORM, sessionmaker)

    async def get_route_by_points(
        self, departure_point_id: int, destination_point_id: int
    ) -> RouteORM:
        """Gets route by departure and destination point IDs."""
        async with self._sessionmaker() as session:
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
        async with self._sessionmaker() as session:
            route = await session.execute(
                select(RouteORM)
                .options(
                    selectinload(RouteORM.departure_point),
                    selectinload(RouteORM.destination_point),
                )
                .where(RouteORM.id == id)
            )
            return route.scalars().first()
