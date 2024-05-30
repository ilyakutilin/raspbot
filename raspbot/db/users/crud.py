from typing import Sequence

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from raspbot.core import exceptions as exc
from raspbot.core.email import send_email_async
from raspbot.core.logging import configure_logging
from raspbot.db.base import async_session_factory
from raspbot.db.crud import CRUDBase
from raspbot.db.models import RecentORM, RouteORM, UserORM
from raspbot.settings import settings

logger = configure_logging(name=__name__)


class CRUDUsers(CRUDBase):
    """CRUD for user related operations."""

    def __init__(self, session: AsyncSession = async_session_factory()):
        """Initializes CRUDUsers class instance."""
        super().__init__(UserORM, session)

    async def get_user_by_telegram_id(self, telegram_id: int) -> UserORM | None:
        """Gets user by Telegram ID."""
        async with self._session as session:
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

    def __init__(self, session: AsyncSession = async_session_factory()):
        """Initializes CRUDRecents class instance."""
        super().__init__(RecentORM, session)

    async def get_recent_or_fav_by_user_id(
        self, user_id: int, fav: bool = False
    ) -> Sequence[RecentORM]:
        """Gets recent or favorite by user ID."""
        async with self._session as session:
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
                    desc(RecentORM.count), desc(RecentORM.updated_at)
                ).limit(settings.RECENT_FAV_LIST_LENGTH)
            )
            return result.scalars().unique().all()

    async def route_in_recent(self, user_id: int, route_id: int) -> RecentORM | None:
        """Checks if a route is in the recents of a user."""
        async with self._session as session:
            query = await session.execute(
                select(RecentORM).where(
                    and_(RecentORM.user_id == user_id, RecentORM.route_id == route_id)
                )
            )
            return query.scalars().first()

    async def update_recent(self, recent_id: int) -> RecentORM:
        """Updates recent 'count' and 'updated_at'."""
        async with self._session as session:
            stmt = (
                update(RecentORM)
                .where(RecentORM.id == recent_id)
                .values(count=RecentORM.count + 1)
            )
            await session.execute(stmt)
            await session.commit()
            try:
                recent_db_new: RecentORM = await self.get_or_raise(_id=recent_id)
            except exc.NoDBObjectError as e:
                logger.exception(e)
                await send_email_async(e)
                raise e
            return recent_db_new

    async def _get_recent_with_route(self, recent_id: int) -> RecentORM:
        """Gets recent with route."""
        async with self._session as session:
            query = await session.execute(
                select(RecentORM)
                .where(RecentORM.id == recent_id)
                .options(
                    joinedload(RecentORM.route).joinedload(RouteORM.departure_point)
                )
                .options(
                    joinedload(RecentORM.route).joinedload(RouteORM.destination_point)
                )
            )
            recent = query.scalars().first()
            if not recent:
                raise exc.NoDBObjectError(f"Recent with ID {recent_id} does not exist.")
            return recent

    async def _add_or_delete_from_fav(
        self, recent_id: int, adding: bool = True
    ) -> RecentORM:
        """Adds or deletes a recent from favorites."""
        async with self._session as session:
            stmt = (
                update(RecentORM)
                .where(RecentORM.id == recent_id)
                .values(favorite=adding)
            )
            await session.execute(stmt)
            await session.commit()
            try:
                recent_db_new: RecentORM = await self._get_recent_with_route(
                    recent_id=recent_id
                )
            except exc.NoDBObjectError as e:
                raise e
            return recent_db_new

    async def add_recent_to_fav(self, recent_id: int) -> RecentORM:
        """Adds a recent to favorites."""
        return await self._add_or_delete_from_fav(recent_id=recent_id, adding=True)

    async def delete_recent_from_fav(self, recent_id: int) -> RecentORM:
        """Deletes a recent from favorites."""
        return await self._add_or_delete_from_fav(recent_id=recent_id, adding=False)
