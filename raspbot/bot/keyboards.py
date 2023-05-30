from aiogram import types

from .constants import commands
from .constants.text import btn


def get_start_keyboard():
    buttons = [
        [
            types.InlineKeyboardButton(
                text=btn.NEW_SEARCH, callback_data=commands.NEW_SEARCH
            )
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
