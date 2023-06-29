from typing import Generator

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.models import Point, Recent, Route, User


class CRUDUsers(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(User, sessionmaker)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self._sessionmaker() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return user.scalars().first()

    async def get_recent_by_user_id(self, user_id: int) -> list[Recent]:
        departure_point_alias = aliased(Point)
        destination_point_alias = aliased(Point)
        async with self._sessionmaker() as session:
            recent = await session.execute(
                select(Recent)
                .where(Recent.user_id == user_id)
                .join(Route)
                .join(departure_point_alias, Route.departure_point)
                .join(destination_point_alias, Route.destination_point)
                .options(joinedload(Recent.route).joinedload(Route.departure_point))
                .options(joinedload(Recent.route).joinedload(Route.destination_point))
                .order_by(desc(Recent.updated_on))
                .limit(10)
            )
            return recent.scalars().unique().all()
