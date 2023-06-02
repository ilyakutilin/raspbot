from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback
from raspbot.bot.constants.states import Route
from raspbot.bot.constants.text import SinglePointFound, msg
from raspbot.bot.keyboards import get_point_choice_keyboard, get_start_keyboard
from raspbot.db.stations.schema import PointResponse
from raspbot.services.routes import point_retriever, point_selector

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
    """User: issues /start command. Bot: please input the departure point."""
    await callback.message.answer(msg.INPUT_DEPARTURE_POINT)
    await callback.answer()
    await state.set_state(Route.choosing_departure_point)


def _single_point_found_message_text(
    point: PointResponse,
    is_departure: bool,
) -> str:
    single_point_found = SinglePointFound(
        is_departure=is_departure,
        is_station=point.is_station,
        title=point.title,
        region_title=point.region_title,
    )
    return str(single_point_found)


@router.message(Route.choosing_departure_point)
async def departure_selected(message: types.Message, state: FSMContext):
    """User: inputs the desired departure point. Bot: here's what I have in the DB."""
    departure_points: list[PointResponse] = await point_selector.select_points(
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
        msg_text: str = _single_point_found_message_text(
            point=departure_points[0], is_departure=True
        )
        await message.answer(text=f"{msg_text}\n{msg.INPUT_DESTINATION_POINT}")
        await state.update_data(departure_point=departure_points[0])
        await state.set_state(Route.choosing_destination_point)


@router.message(Route.choosing_destination_point)
async def destination_selected(message: types.Message, state: FSMContext):
    """User: inputs the destination point. Bot: here's what I have in the DB."""
    destination_points: list[PointResponse] = await point_selector.select_points(
        raw_user_input=message.text
    )
    if not destination_points:
        await message.answer(text=msg.POINT_NOT_FOUND)
    elif len(destination_points) > 1:
        await message.answer(
            msg.MULTIPLE_POINTS_FOUND,
            reply_markup=get_point_choice_keyboard(
                points=destination_points, is_departure=False
            ),
        )
        await state.set_state(Route.choosing_point_from_multiple)
    else:
        msg_text: str = _single_point_found_message_text(
            point=destination_points[0], is_departure=False
        )
        await message.answer(text=msg_text)
        await state.update_data(destination_point=destination_points[0])
        await state.set_state(Route.getting_timetable_between_points)


@router.callback_query(Text(startswith=callback.MISSING_POINT[:-1]))
async def missing_point_callback(callback: types.CallbackQuery, state: FSMContext):
    """User: clicks the 'missing' button. Bot: please start again."""
    is_departure = bool(int(callback.data[-1]))
    await callback.message.answer(
        msg.INPUT_DEPARTURE_POINT if is_departure else msg.INPUT_DESTINATION_POINT
    )
    await callback.answer()
    await state.set_state(
        Route.choosing_departure_point
        if is_departure
        else Route.choosing_destination_point
    )


@router.callback_query(callback.PointsCallbackFactory.filter())
async def choose_point_from_multiple_callback(
    callback: types.CallbackQuery,
    callback_data: callback.PointsCallbackFactory,
    state: FSMContext,
):
    """User: selects the point from the list. Bot: input the destination point."""
    selected_point: PointResponse = await point_retriever.get_point(
        point_id=callback_data.point_id, is_station=callback_data.is_station
    )
    if callback_data.is_departure:
        msg_text: str = _single_point_found_message_text(
            point=selected_point, is_departure=callback_data.is_departure
        )
        await callback.message.answer(text=f"{msg_text}\n{msg.INPUT_DESTINATION_POINT}")
        await callback.answer()
        await state.update_data(departure_point=selected_point)
        await state.set_state(Route.choosing_destination_point)
    else:
        await state.set_state(Route.getting_timetable_between_points)
