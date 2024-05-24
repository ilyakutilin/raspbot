from aiogram import types
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from raspbot.bot.constants import messages as msg
from raspbot.bot.start.keyboards import back_to_start_keyboard
from raspbot.core.email import send_email_async
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import UserORM
from raspbot.services.users import create_user, get_user_from_db

logger = configure_logging(__name__)


@log(logger)
async def get_command_user(  # type: ignore
    command: str,
    message: types.Message,
    reply_text: str | None = None,
    reply_markup: types.ReplyKeyboardMarkup | None = None,
) -> tuple[UserORM, bool]:
    """Gets the user from the DB for the Telegram command. Creates if doesn't exist.

    Returns the user object and boolean for whether the user is new (True)
    or existing (False).
    """
    assert message.from_user
    try:
        user = await get_user_from_db(telegram_id=message.from_user.id)
    except (SQLAlchemyError, DBAPIError) as e:
        logger.exception(e)
        await send_email_async(e)
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
        raise e

    if not user:
        logger.info(
            f"New user detected: {message.from_user.full_name}, "
            f"telegram id = {message.from_user.id}. Adding to DB."
        )
        try:
            user = await create_user(tg_user=message.from_user)
        except (SQLAlchemyError, DBAPIError) as e:
            logger.exception(e)
            await send_email_async(e)
            await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
            raise e

        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /{command} "
            "command. Replying."
        )
        if reply_text:
            await message.answer(
                text=reply_text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        return user, True

    return user, False
