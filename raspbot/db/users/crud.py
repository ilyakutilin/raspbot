from typing import Generator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.users.models import User


class CRUDUsers(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(User, sessionmaker)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self._sessionmaker() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return user.scalars().first()
