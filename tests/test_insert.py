import pytest

from raspbot.db.users.crud import CRUDUsers
from raspbot.db.users.models import UserORM


@pytest.mark.asyncio
async def test_read(session):
    """Test read."""
    crud_users = CRUDUsers(session)
    result: UserORM | None = await crud_users.get_user_by_telegram_id(1)
    assert result is None


@pytest.mark.asyncio
async def test_db_insert(session):
    """Test insert."""
    crud_users = CRUDUsers(session)
    new_obj = UserORM(
        telegram_id=1,
        first_name="John",
        last_name="Doe",
        username="john_doe",
    )
    session.add(new_obj)
    await session.commit()

    result: UserORM | None = await crud_users.get_user_by_telegram_id(1)
    assert result.full_name == "John Doe"
