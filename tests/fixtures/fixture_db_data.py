import pytest_asyncio

from raspbot.db.users.crud import CRUDUsers
from raspbot.db.users.models import UserORM


@pytest_asyncio.fixture(scope="session")
async def user(session):
    """User fixture."""
    crud_users = CRUDUsers(session)
    new_obj = UserORM(
        telegram_id=2147483648,
        first_name="John",
        last_name="Doe",
        username="john_doe",
    )
    session.add(new_obj)
    await session.commit()

    user: UserORM | None = await crud_users.get_user_by_telegram_id(1)
    yield user

    await session.rollback()
