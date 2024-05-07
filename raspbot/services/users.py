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
    Получает объект пользователя из БД или None при его отсутствии.

    Принимает на вход:
        telegram_id (int): Telegram ID пользователя.

    Возвращает:
        Объект пользователя (User) или None.
    """
    user_from_db: UserORM | None = await crud_users.get_user_by_telegram_id(
        telegram_id=telegram_id
    )
    if not user_from_db:
        logger.debug(f"Пользователя с telegram_id {telegram_id} нет в базе.")
        return None
    logger.debug(
        f"Пользователь с telegram_id {telegram_id} есть в базе, "
        f"id {user_from_db.id}, его зовут "
        f"{user_from_db.first_name} {user_from_db.last_name}."
    )
    return user_from_db


@log(logger)
async def create_user(tg_user: TgUser) -> UserORM:
    """
    Создает пользователя в БД.

    Принимает на вход:
        tg_user (TgUser): Объект пользователя aiogram.

    Возвращает:
        User: объект пользователя.
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
async def get_user_recent(user: UserORM) -> list[RecentORM] | None:
    """Get user recent routes."""
    return await crud_recents.get_recent_or_fav_by_user_id(user_id=user.id, fav=False)


@log(logger)
async def get_user_fav(user: UserORM) -> list[RecentORM] | None:
    """Get user favorite routes."""
    return await crud_recents.get_recent_or_fav_by_user_id(user_id=user.id, fav=True)


@log(logger)
async def update_recent(recent_id: int) -> RecentORM:
    """Update recent count and update date."""
    recent = await crud_recents.get_or_none(_id=recent_id)
    update_date_before = recent.updated_at
    logger.info(
        "Здесь должна происходить магия обновления даты. До обновления: "
        f"ID пользователя {recent.user_id}, ID маршрута {recent.route_id}"
        f", дата создания {recent.created_at}, "
        f"дата обновления {update_date_before}."
    )

    updated_element = await crud_recents.update_recent(recent_id=recent_id)
    if updated_element.updated_at == update_date_before:
        logger.warning(
            "Обновление даты не получилось: дата по-прежнему "
            f"{updated_element.updated_at}."
        )
    else:
        logger.info(f"Дата обновлена: новая дата {updated_element.updated_at}")
    return updated_element


@log(logger)
async def add_or_update_recent(user_id: int, route_id: int):
    """Add or update user recent route."""
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
    """Add recent to user favorite routes."""
    return await crud_recents.add_recent_to_fav(recent_id=recent_id)
