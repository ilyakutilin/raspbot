from aiogram import Router, types
from aiogram.filters import Command, Text

from raspbot.bot.constants import commands
from raspbot.bot.constants.text import msg
from raspbot.bot.keyboards import get_start_keyboard

router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        text=msg.GREETING.format(name=message.from_user.first_name),
        reply_markup=get_start_keyboard(),
    )

