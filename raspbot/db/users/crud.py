from typing import Generator

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from raspbot.core.logging import configure_logging
from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.models import Recent, Route, User
from raspbot.settings import settings

logger = configure_logging(name=__name__)


class CRUDUsers(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(User, sessionmaker)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self._sessionmaker() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return user.scalars().first()


class CRUDRecents(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(Recent, sessionmaker)

    async def get_recent_or_fav_by_user_id(
        self, user_id: int, fav: bool = False
    ) -> list[Recent]:
        async with self._sessionmaker() as session:
            selection = (
                select(Recent)
                .where(Recent.user_id == user_id)
                .join(Route)
                .options(joinedload(Recent.route).joinedload(Route.departure_point))
                .options(joinedload(Recent.route).joinedload(Route.destination_point))
            )
            if fav:
                selection = selection.where(Recent.favorite == True)  # noqa
            result = await session.execute(
                selection.order_by(desc(Recent.count), desc(Recent.updated_on)).limit(
                    settings.RECENT_FAV_LIST_LENGTH
                )
            )
            return result.scalars().unique().all()

    async def route_in_recent(self, user_id: int, route_id: int) -> Recent | None:
        async with self._sessionmaker() as session:
            query = await session.execute(
                select(Recent).where(
                    and_(Recent.user_id == user_id, Recent.route_id == route_id)
                )
            )
            return query.scalars().first()

    async def update_recent(self, recent_id: Recent) -> Recent:
        async with self._sessionmaker() as session:
            stmt = (
                update(Recent)
                .where(Recent.id == recent_id)
                .values(count=Recent.count + 1)
            )
            await session.execute(stmt)
            await session.commit()
            recent_db_new: Recent = await self.get_or_none(_id=recent_id)
            return recent_db_new

    async def add_recent_to_fav(self, recent_id: int) -> Recent:
        async with self._sessionmaker() as session:
            stmt = update(Recent).where(Recent.id == recent_id).values(favorite=True)
            await session.execute(stmt)
            await session.commit()
            recent_db_new: Recent = await self.get_or_none(_id=recent_id)
            return recent_db_new
