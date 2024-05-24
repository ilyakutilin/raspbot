from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.start.keyboards import start_keyboard
from raspbot.bot.start.utils import get_command_user
from raspbot.core.logging import configure_logging

logger = configure_logging(name=__name__)

router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message):
    """User: issues /start command. Bot: please input the departure point."""
    assert message.from_user
    user, new_user = await get_command_user(
        command="start",
        message=message,
        reply_text=msg.GREETING_NEW_USER.format(
            first_name=message.from_user.first_name
        ),
        reply_markup=start_keyboard,
    )

    if not new_user:
        logger.info(
            f"User {user.full_name} TGID {user.telegram_id} issued a /start command. "
            "Greeting existing user."
        )
        await message.answer(
            msg.GREETING_EXISTING_USER.format(first_name=user.first_name),
            reply_markup=start_keyboard,
            parse_mode="HTML",
        )


@router.callback_query(F.data == clb.START)
async def start_callback(callback: types.CallbackQuery, state: FSMContext):
    """User: clicks the 'Go back to the start' button. Bot: start."""
    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} clicked on "
        "the 'Go back to the start' inline button. Replying."
    )
    await state.clear()
    assert isinstance(callback.message, types.Message)
    await callback.message.answer(
        text=msg.GREETING_EXISTING_USER,
        reply_markup=start_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()
