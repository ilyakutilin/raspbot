from typing import Generator

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from raspbot.core.logging import configure_logging
from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.models import RecentORM, RouteORM, UserORM
from raspbot.settings import settings

logger = configure_logging(name=__name__)


class CRUDUsers(CRUDBase):
    """CRUD for user related operations."""

    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        """Initializes CRUDUsers class instance."""
        super().__init__(UserORM, sessionmaker)

    async def get_user_by_telegram_id(self, telegram_id: int) -> UserORM | None:
        """Gets user by Telegram ID."""
        async with self._sessionmaker() as session:
            user = await session.execute(
                select(UserORM).where(UserORM.telegram_id == telegram_id)
            )
            return user.scalars().first()


class CRUDRecents(CRUDBase):
    """CRUD for user recent and favorites related operations.

    Recent and favorite is the same model Recent.
    Favorite is implemented by a 'favorite' boolean field.
    A route needs to be in the recents to be added to favorites.
    """

    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        """Initializes CRUDRecents class instance."""
        super().__init__(RecentORM, sessionmaker)

    async def get_recent_or_fav_by_user_id(
        self, user_id: int, fav: bool = False
    ) -> list[RecentORM]:
        """Gets recent or favorite by user ID."""
        async with self._sessionmaker() as session:
            selection = (
                select(RecentORM)
                .where(RecentORM.user_id == user_id)
                .join(RouteORM)
                .options(
                    joinedload(RecentORM.route).joinedload(RouteORM.departure_point)
                )
                .options(
                    joinedload(RecentORM.route).joinedload(RouteORM.destination_point)
                )
            )
            if fav:
                selection = selection.where(RecentORM.favorite == True)  # noqa
            result = await session.execute(
                selection.order_by(
                    desc(RecentORM.count), desc(RecentORM.updated_on)
                ).limit(settings.RECENT_FAV_LIST_LENGTH)
            )
            return result.scalars().unique().all()

    async def route_in_recent(self, user_id: int, route_id: int) -> RecentORM | None:
        """Checks if a route is in the recents of a user."""
        async with self._sessionmaker() as session:
            query = await session.execute(
                select(RecentORM).where(
                    and_(RecentORM.user_id == user_id, RecentORM.route_id == route_id)
                )
            )
            return query.scalars().first()

    async def update_recent(self, recent_id: RecentORM) -> RecentORM:
        """Updates recent 'count' and 'updated_on'."""
        async with self._sessionmaker() as session:
            stmt = (
                update(RecentORM)
                .where(RecentORM.id == recent_id)
                .values(count=RecentORM.count + 1)
            )
            await session.execute(stmt)
            await session.commit()
            recent_db_new: RecentORM = await self.get_or_none(_id=recent_id)
            return recent_db_new

    async def add_recent_to_fav(self, recent_id: int) -> RecentORM:
        """Adds a recent to favorites."""
        async with self._sessionmaker() as session:
            stmt = (
                update(RecentORM).where(RecentORM.id == recent_id).values(favorite=True)
            )
            await session.execute(stmt)
            await session.commit()
            recent_db_new: RecentORM = await self.get_or_none(_id=recent_id)
            return recent_db_new
