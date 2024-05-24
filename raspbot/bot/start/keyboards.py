from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raspbot.bot.constants import buttons as btn
from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging

logger = configure_logging(name=__name__)

kb = [
    [
        types.KeyboardButton(text=btn.NEW_SEARCH_COMMAND),
        types.KeyboardButton(text=btn.RECENTS_COMMAND),
        types.KeyboardButton(text=btn.FAVORITES_COMMAND),
    ],
]
start_keyboard = types.ReplyKeyboardMarkup(
    keyboard=kb,
    resize_keyboard=True,
)


def back_to_start_keyboard() -> types.InlineKeyboardMarkup:
    """Keyboard with a single button for going back to the start."""
    builder = InlineKeyboardBuilder()
    builder.button(text=btn.START, callback_data=clb.START)
    builder.adjust(1)
    logger.info(f"back_to_start_keyboard contains {len(set(builder.buttons))} buttons.")
    return builder.as_markup()
