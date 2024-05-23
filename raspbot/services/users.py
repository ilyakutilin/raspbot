from typing import Sequence

from aiogram.types.user import User as TgUser

from raspbot.core.logging import configure_logging, log
from raspbot.db.models import RecentORM, UserORM
from raspbot.db.users.crud import CRUDRecents, CRUDUsers

logger = configure_logging(name=__name__)

crud_users = CRUDUsers()
crud_recents = CRUDRecents()


@log(logger)
async def get_user_from_db(telegram_id: int) -> UserORM | None:
    """
    Gets the user object from the database, or None if it does not exist.

    Accepts:
        telegram_id (int): the user's Telegram ID.

    Returns:
        User object (User) or None.
    """
    user_from_db: UserORM | None = await crud_users.get_user_by_telegram_id(
        telegram_id=telegram_id
    )
    if not user_from_db:
        logger.debug(f"User with telegram_id {telegram_id} is not in DB.")
        return None
    logger.debug(
        f"User with telegram_id {telegram_id} exists in DB, "
        f"DB id {user_from_db.id}, their name is {user_from_db.full_name}."
    )
    return user_from_db


@log(logger)
async def create_user(tg_user: TgUser) -> UserORM:
    """
    Creates a user in the database.

    Accepts:
        tg_user (TgUser): The aiogram user object.

    Returns:
        User: User object.
    """
    instance = UserORM(
        telegram_id=tg_user.id,
        is_bot=tg_user.is_bot,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        username=tg_user.username,
        language_code=tg_user.language_code,
    )
    user_db: UserORM = await crud_users.create(instance=instance)
    return user_db


@log(logger)
async def get_user_recent(user: UserORM) -> Sequence[RecentORM]:
    """Gets user recent routes."""
    return await crud_recents.get_recent_or_fav_by_user_id(user_id=user.id, fav=False)


@log(logger)
async def get_user_fav(user: UserORM) -> Sequence[RecentORM]:
    """Gets user favorite routes."""
    return await crud_recents.get_recent_or_fav_by_user_id(user_id=user.id, fav=True)


@log(logger)
async def update_recent(recent_id: int) -> RecentORM:
    """Updates recent count and update date."""
    recent: RecentORM = await crud_recents.get_or_raise(_id=recent_id)
    update_date_before = recent.updated_at
    logger.info(
        "Updating the update date. Before update: "
        f"User ID {recent.user_id}, Route ID {recent.route_id}"
        f", created_at {recent.created_at}, updated_at {update_date_before}."
    )

    updated_element = await crud_recents.update_recent(recent_id=recent_id)
    if updated_element.updated_at == update_date_before:
        logger.warning(
            "Date update failed. The updated_at is still "
            f"{updated_element.updated_at}."
        )
    else:
        logger.info(
            f"Date has been updated: new updated_at: {updated_element.updated_at}"
        )
    return updated_element


@log(logger)
async def add_or_update_recent(user_id: int, route_id: int):
    """Adds or updates user recent route."""
    route_added: RecentORM | None = await crud_recents.route_in_recent(
        user_id=user_id, route_id=route_id
    )
    if not route_added:
        instance = RecentORM(user_id=user_id, route_id=route_id, count=1)
        await crud_recents.create(instance=instance)
    else:
        await update_recent(recent_id=route_added.id)


@log(logger)
async def add_recent_to_fav(recent_id: int) -> RecentORM:
    """Adds recent to user favorite routes."""
    return await crud_recents.add_recent_to_fav(recent_id=recent_id)
