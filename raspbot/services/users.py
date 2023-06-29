from aiogram.types.user import User as TgUser

from raspbot.core.logging import configure_logging
from raspbot.db.users.crud import CRUDUsers
from raspbot.db.users.models import Recent, User

logger = configure_logging(name=__name__)

crud_users = CRUDUsers()


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


async def get_user_recent(user: User) -> list[Recent] | None:
    return await crud_users.get_recent_by_user_id(user_id=user.id)
