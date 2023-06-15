from typing import Generator

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from raspbot.apicalls.search import TransportTypes
from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.stations.models import Country, Point


class CRUDPoints(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(Point, sessionmaker)

    async def get_points_by_title(
        self, title: str, strict_search: bool = False
    ) -> list[Point]:
        search_template = "{title}" if strict_search else "%{title}%"
        async with self._sessionmaker() as session:
            points = await session.execute(
                select(Point)
                .options(selectinload(Point.region))
                .join(Country)
                .where(
                    func.unaccent(Point.title).ilike(
                        search_template.format(title=title)
                    )
                )
                .where(Country.title == "Россия")
                .where(
                    or_(
                        Point.transport_type == TransportTypes.TRAIN.value,
                        Point.transport_type.is_(None),
                    )
                )
                .order_by(Point.title)
                .limit(30)
            )
            return points.scalars().unique().all()

    async def get_point_by_id(self, id: int) -> Point:
        async with self._sessionmaker() as session:
            point = await session.execute(
                select(Point).options(selectinload(Point.region)).where(Point.id == id)
            )
            return point.scalars().first()
