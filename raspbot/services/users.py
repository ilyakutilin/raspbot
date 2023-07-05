from aiogram.types.user import User as TgUser

from raspbot.core.logging import configure_logging, log
from raspbot.db.models import Recent, User
from raspbot.db.users.crud import CRUDRecents, CRUDUsers

logger = configure_logging(name=__name__)

crud_users = CRUDUsers()
crud_recents = CRUDRecents()


@log(logger)
async def get_user_from_db(telegram_id: int) -> User | None:
    """
    Получает объект пользователя из БД или None при его отсутствии.

    Принимает на вход:
        telegram_id (int): Telegram ID пользователя.

    Возвращает:
        Объект пользователя (User) или None.
    """
    user_from_db: User = await crud_users.get_user_by_telegram_id(
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
async def create_user(tg_user: TgUser) -> User:
    """
    Создает пользователя в БД.

    Принимает на вход:
        tg_user (TgUser): Объект пользователя aiogram.

    Возвращает:
        User: объект пользователя.
    """
    instance = User(
        telegram_id=tg_user.id,
        is_bot=tg_user.is_bot,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        username=tg_user.username,
        language_code=tg_user.language_code,
    )
    user_db: User = await crud_users.create(instance=instance)
    return user_db


@log(logger)
async def get_user_recent(user: User) -> list[Recent] | None:
    return await crud_recents.get_recent_or_fav_by_user_id(user_id=user.id, fav=False)


@log(logger)
async def get_user_fav(user: User) -> list[Recent] | None:
    return await crud_recents.get_recent_or_fav_by_user_id(user_id=user.id, fav=True)


@log(logger)
async def update_recent(recent_id: int) -> Recent:
    recent = await crud_recents.get_or_none(_id=recent_id)
    update_date_before = recent.updated_on
    logger.info(
        "Здесь должна происходить магия обновления даты. До обновления: "
        f"ID пользователя {recent.user_id}, ID маршрута {recent.route_id}"
        f", дата создания {recent.added_on}, "
        f"дата обновления {update_date_before}."
    )

    updated_element = await crud_recents.update_recent(recent_id=recent_id)
    if updated_element.updated_on == update_date_before:
        logger.warning(
            "Обновление даты не получилось: дата по-прежнему "
            f"{updated_element.updated_on}."
        )
    else:
        logger.info(f"Дата обновлена: новая дата {updated_element.updated_on}")
    return updated_element


@log(logger)
async def add_or_update_recent(user_id: int, route_id: int):
    route_added: Recent | None = await crud_recents.route_in_recent(
        user_id=user_id, route_id=route_id
    )
    if not route_added:
        instance = Recent(user_id=user_id, route_id=route_id, count=1)
        await crud_recents.create(instance=instance)
    else:
        await update_recent(recent_id=route_added.id)


@log(logger)
async def add_recent_to_fav(recent_id: int) -> Recent:
    return await crud_recents.add_recent_to_fav(recent_id=recent_id)
