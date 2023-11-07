from aiogram import F, Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.routes.keyboards import (
    get_point_choice_keyboard,
    get_single_point_confirmation_keyboard,
)
from raspbot.bot.timetable.handlers import process_timetable_callback
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.models import User
from raspbot.db.routes.schema import PointResponse, RouteResponse
from raspbot.services.routes import PointRetriever, PointSelector, RouteFinder
from raspbot.services.timetable import TodayTimetable
from raspbot.services.users import get_user_from_db
from raspbot.settings import settings

logger = configure_logging(name=__name__)

router = Router()

point_retriever = PointRetriever()
route_finder = RouteFinder()


@router.message(Command("search"))
async def search_command(message: types.Message, state: FSMContext):
    """User: issues /search command. Bot: please input the departure point."""
    await message.answer(msg.INPUT_DEPARTURE_POINT)
    await state.set_state(states.RouteState.selecting_departure_point)


@router.callback_query(Text(text=clb.NEW_SEARCH))
async def new_search_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(msg.INPUT_DEPARTURE_POINT)
    await state.set_state(states.RouteState.selecting_departure_point)
    await callback.answer()


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
        msg_text: str = msg.SinglePointFound(point=point, is_departure=is_departure)
        await message.answer(
            text=f"{msg_text} {msg.WHAT_YOU_WERE_LOOKING_FOR}",
            reply_markup=get_single_point_confirmation_keyboard(
                point=point, is_departure=is_departure
            ),
        )


@router.message(states.RouteState.selecting_departure_point)
async def select_departure(message: types.Message, state: FSMContext):
    """User: inputs the desired departure point. Bot: here's what I have in the DB."""
    await select_point(is_departure=True, message=message, state=state)


@router.message(states.RouteState.selecting_destination_point)
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
        states.RouteState.selecting_departure_point
        if is_departure
        else states.RouteState.selecting_destination_point
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
    msg_text: str = msg.SinglePointFound(
        point=selected_departure, is_departure=callback_data.is_departure
    )
    await callback.message.answer(text=f"{msg_text}\n{msg.INPUT_DESTINATION_POINT}")
    await callback.answer()
    await state.update_data(departure_point=selected_departure)
    await state.set_state(states.RouteState.selecting_destination_point)


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
    msg_text = msg.SinglePointFound(
        point=selected_point, is_departure=callback_data.is_departure
    )
    user_data: dict = await state.get_data()
    try:
        departure_point: PointResponse = user_data["departure_point"]
    except ValueError as e:
        logger.error(f"Departure point is not found in the state data: {e}")
        callback.message.answer(text=msg.ERROR)
    user: User = await get_user_from_db(telegram_id=callback.from_user.id)
    route: RouteResponse = await route_finder.get_or_create_route(
        departure_point=departure_point, destination_point=selected_point, user=user
    )
    timetable_obj = TodayTimetable(route=route, limit=settings.CLOSEST_DEP_LIMIT)
    logger.debug(f"Creating timetable_obj: {timetable_obj.__dict__}")
    await process_timetable_callback(
        callback=callback,
        state=state,
        timetable_obj=timetable_obj,
        add_msg_text=str(msg_text),
    )
