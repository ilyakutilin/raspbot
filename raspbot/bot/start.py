from aiogram import Router, types
from aiogram.filters import Command

from raspbot.core.logging import configure_logging
from raspbot.services.users import create_user, get_user_from_db

logger = configure_logging(name=__name__)

router = Router()

GREETING_NEW_USER = (
    "Здравствуйте, {first_name}! ✋\n\nВы раньше у нас не были, поэтому вам доступна "
    "только функция нового поиска. Для этого нажмите <b>/search</b> и следуйте "
    "указаниям."
)
GREETING_EXISTING_USER = (
    "Здравствуйте, {first_name}! ✋\n\n<b>/search</b> - Новый поиск\n"
    "<b>/last</b> - Ваши недавние маршруты\n<b>/fav</b> - Ваше избранное"
)

NEW_SEARCH = "/search"
RECENTS = "/last"
FAVORITES = "/fav"


kb = [
    [
        types.KeyboardButton(text=NEW_SEARCH),
        types.KeyboardButton(text=RECENTS),
        types.KeyboardButton(text=FAVORITES),
    ],
]
keyboard = types.ReplyKeyboardMarkup(
    keyboard=kb,
    resize_keyboard=True,
)


@router.message(Command("start"))
async def start_command(message: types.Message):
    """User: issues /start command. Bot: please input the departure point."""
    user = await get_user_from_db(telegram_id=message.from_user.id)
    if not user:
        user = await create_user(tg_user=message.from_user)
        await message.answer(
            GREETING_NEW_USER.format(first_name=message.from_user.first_name),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            GREETING_EXISTING_USER.format(first_name=user.first_name),
            reply_markup=keyboard,
        )
