from typing import Generator

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.models import Favorite, Recent, Route, User


class CRUDUsers(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(User, sessionmaker)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self._sessionmaker() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return user.scalars().first()

    async def get_recent_or_fav_by_user_id(
        self, user_id: int, model: Recent | Favorite
    ) -> list[Recent | Favorite]:
        async with self._sessionmaker() as session:
            recent = await session.execute(
                select(model)
                .where(model.user_id == user_id)
                .join(Route)
                .options(joinedload(model.route).joinedload(Route.departure_point))
                .options(joinedload(model.route).joinedload(Route.destination_point))
                .order_by(desc(model.updated_on))
                .limit(10)
            )
            return recent.scalars().unique().all()
