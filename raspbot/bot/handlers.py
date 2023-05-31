from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback
from raspbot.bot.constants.states import Route
from raspbot.bot.constants.text import msg, wrd
from raspbot.bot.keyboards import get_point_choice_keyboard, get_start_keyboard
from raspbot.db.stations.schema import PointResponse
from raspbot.services.routes import select_points

router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message):
    """Start command."""
    await message.answer(
        text=msg.GREETING.format(name=message.from_user.first_name),
        reply_markup=get_start_keyboard(),
    )


@router.callback_query(Text(callback.SELECT_DEPARTURE))
async def select_departure_callback(callback: types.CallbackQuery, state: FSMContext):
    """User: issues /start command. Bot: please select the departure point."""
    await callback.message.answer(msg.INPUT_DEPARTURE_POINT)
    await callback.answer()
    await state.set_state(Route.choosing_departure_point)


@router.message(Route.choosing_departure_point)
async def departure_selected(message: types.Message, state: FSMContext):
    departure_points: list[PointResponse] = await select_points(
        raw_user_input=message.text
    )
    if not departure_points:
        await message.answer(text=msg.POINT_NOT_FOUND)
    elif len(departure_points) > 1:
        await message.answer(
            msg.MULTIPLE_POINTS_FOUND,
            reply_markup=get_point_choice_keyboard(
                points=departure_points, is_departure=True
            ),
        )
        await state.set_state(Route.choosing_point_from_multiple)
    else:
        departure_point = departure_points[0]
        departure_point_type = wrd.STATION if departure_point.is_station else wrd.CITY
        await message.answer(
            msg.SINGLE_POINT_FOUND.format(
                departure_point_type=departure_point_type,
                departure_point_name=departure_point.title,
                departure_point_region=departure_point.region_title,
            )
        )
        await state.set_state(Route.choosing_destination_point)
