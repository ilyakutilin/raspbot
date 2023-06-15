from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from raspbot.bot.routes.constants import callback as clb
from raspbot.bot.routes.constants.states import Route
from raspbot.bot.routes.constants.text import SinglePointFound, msg
from raspbot.bot.routes.keyboards import (
    get_point_choice_keyboard,
    get_single_point_confirmation_keyboard,
)
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.routes.schema import PointResponse
from raspbot.services.routes import PointRetriever, PointSelector
from raspbot.services.timetable import search_timetable

logger = configure_logging(name=__name__)

router = Router()

point_retriever = PointRetriever()


@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """User: issues /start command. Bot: please input the departure point."""
    logger.debug(f"User data: {message.from_user}")
    await message.answer(msg.INPUT_DEPARTURE_POINT)
    await state.set_state(Route.selecting_departure_point)


async def select_point(is_departure: bool, message: types.Message, state: FSMContext):
    """Base function for the departure / destination point selection."""
    point_selector = PointSelector()
    try:
        point_chunks: list[list[PointResponse]] = await point_selector.select_points(
            raw_user_input=message.text
        )
    except exc.UserInputTooShortError as e:
        logger.error(e, exc_info=True)
        await message.answer(text=msg.INPUT_TOO_SHORT)
    if not point_chunks:
        await message.answer(text=msg.POINT_NOT_FOUND)
    elif len(point_chunks) > 1 or len(point_chunks[0]) > 1:
        logger.debug(f"Number of point chunks before pop: {len(point_chunks)}.")
        points: list = point_chunks.pop(0)
        logger.debug(f"First point chunk popped, its length is {len(points)} elements.")
        logger.debug(f"Number of point chunks after pop is {len(point_chunks)} chunks.")
        logger.debug(
            f"Bool value of last chunk given to keyboard is {not point_chunks}."
        )
        await message.answer(
            msg.MULTIPLE_POINTS_FOUND,
            reply_markup=get_point_choice_keyboard(
                points=points, is_departure=is_departure, last_chunk=not point_chunks
            ),
        )
        await state.update_data(remaining_point_chunks=point_chunks)
        user_data: dict = await state.get_data()
        logger.debug(
            "Amount of remaining chunks in the state user data is "
            f"{len(user_data['remaining_point_chunks'])} chunks."
        )
    else:
        point = point_chunks[0][0]
        msg_text: str = SinglePointFound(point=point, is_departure=is_departure)
        await message.answer(
            text=f"{msg_text} {msg.WHAT_YOU_WERE_LOOKING_FOR}",
            reply_markup=get_single_point_confirmation_keyboard(
                point=point, is_departure=is_departure
            ),
        )


@router.message(Route.selecting_departure_point)
async def select_departure(message: types.Message, state: FSMContext):
    """User: inputs the desired departure point. Bot: here's what I have in the DB."""
    await select_point(is_departure=True, message=message, state=state)


@router.message(Route.selecting_destination_point)
async def select_destination(message: types.Message, state: FSMContext):
    """User: inputs the destination point. Bot: here's what I have in the DB."""
    await select_point(is_departure=False, message=message, state=state)


@router.callback_query(clb.MorePointCunksCallbackFactory.filter())
async def more_buttons_handler(
    callback: types.CallbackQuery,
    callback_data: clb.MorePointCunksCallbackFactory,
    state: FSMContext,
):
    user_data: dict = await state.get_data()

    point_chunks: list[list[PointResponse]] = user_data["remaining_point_chunks"]
    points: list = point_chunks.pop(0)
    await callback.message.answer(
        msg.MORE_POINT_CHOICES,
        reply_markup=get_point_choice_keyboard(
            points=points,
            is_departure=callback_data.is_departure,
            last_chunk=not point_chunks,
        ),
    )
    await state.update_data(remaining_point_chunks=point_chunks)
    await callback.answer()


@router.callback_query(clb.MissingPointCallbackFactory.filter())
async def missing_point_callback(
    callback: types.CallbackQuery,
    callback_data: clb.MissingPointCallbackFactory,
    state: FSMContext,
):
    """User: clicks the 'missing' button. Bot: please start again."""
    is_departure: bool = callback_data.is_departure
    await callback.message.answer(msg.MISSING_POINT)
    await callback.answer()
    await state.set_state(
        Route.selecting_departure_point
        if is_departure
        else Route.selecting_destination_point
    )


@router.callback_query(clb.PointsCallbackFactory.filter(F.is_departure == True))  # noqa
async def choose_departure_from_multiple_callback(
    callback: types.CallbackQuery,
    callback_data: clb.PointsCallbackFactory,
    state: FSMContext,
):
    """User: selects the departure from the list. Bot: input the destination point."""
    selected_departure: PointResponse = await point_retriever.get_point(
        point_id=callback_data.point_id
    )
    msg_text: str = SinglePointFound(
        point=selected_departure, is_departure=callback_data.is_departure
    )
    await callback.message.answer(text=f"{msg_text}\n{msg.INPUT_DESTINATION_POINT}")
    await callback.answer()
    await state.update_data(departure_point=selected_departure)
    await state.set_state(Route.selecting_destination_point)


@router.callback_query(
    clb.PointsCallbackFactory.filter(F.is_departure == False)  # noqa
)
async def choose_destination_from_multiple_callback(
    callback: types.CallbackQuery,
    callback_data: clb.PointsCallbackFactory,
    state: FSMContext,
):
    """User: selects the destination from the list. Bot: here's the timetable."""
    selected_point: PointResponse = await point_retriever.get_point(
        point_id=callback_data.point_id
    )
    msg_text: str = SinglePointFound(
        point=selected_point, is_departure=callback_data.is_departure
    )
    user_data: dict = await state.get_data()
    try:
        departure_code: str = user_data["departure_point"].yandex_code
    except ValueError as e:
        logger.error(f"Departure code is not found in the destination founction: {e}")
        callback.message.answer(text=msg.ERROR)
    destination_code: str = selected_point.yandex_code
    timetable: list[str] = await search_timetable(
        departure_code=departure_code, destination_code=destination_code
    )
    await callback.message.answer(
        text=(
            f"{msg_text}\n\n{msg.CLOSEST_DEPARTURES}\n{', '.join(timetable)}\n\n"
            f"{msg.PRESS_DEPARTURE_BUTTON}"
        )
    )
    await callback.answer()
    await state.clear()
