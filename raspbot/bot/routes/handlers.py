from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.routes import utils
from raspbot.bot.routes.keyboards import get_point_choice_keyboard
from raspbot.bot.timetable.utils import process_timetable_callback
from raspbot.core.logging import configure_logging
from raspbot.db.models import UserORM
from raspbot.db.routes.schema import PointResponsePD, RouteResponsePD
from raspbot.services.routes import PointRetriever, RouteFinder
from raspbot.services.timetable import Timetable
from raspbot.services.users import create_user, get_user_from_db
from raspbot.settings import settings

logger = configure_logging(name=__name__)

router = Router()

point_retriever = PointRetriever()
route_finder = RouteFinder()


@router.message(Command("search"))
async def search_command(message: types.Message, state: FSMContext):
    """User: issues /search command. Bot: please input the departure point."""
    user = await get_user_from_db(telegram_id=message.from_user.id)
    if not user:
        logger.info(
            f"New user detected: {message.from_user.full_name}, "
            f"telegram id = {message.from_user.id}. Adding to DB."
        )
        user = await create_user(tg_user=message.from_user)

    logger.info(
        f"User {user.full_name} TGID {user.telegram_id} issued a /search command. "
        "Replying."
    )
    await message.answer(msg.INPUT_DEPARTURE_POINT)

    logger.info("Setting state to 'selecting_departure_point'.")
    await state.set_state(states.RouteState.selecting_departure_point)


@router.callback_query(F.data == clb.NEW_SEARCH)
async def new_search_callback(callback: types.CallbackQuery, state: FSMContext):
    """User: clicks the 'new search' button. Bot: please input the departure point."""
    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} clicked on "
        "the 'New Search' inline button. Replying."
    )
    await callback.message.answer(msg.INPUT_DEPARTURE_POINT)

    logger.info("Setting state to 'selecting_departure_point'.")
    await state.set_state(states.RouteState.selecting_departure_point)

    await callback.answer()


@router.message(states.RouteState.selecting_departure_point)
async def select_departure(message: types.Message, state: FSMContext):
    """User: inputs the desired departure point. Bot: here's what I have in the DB."""
    logger.info(
        f"User {message.from_user.full_name} TGID {message.from_user.id} entered the "
        f"departure point '{message.text}'. Searching for the point in the DB."
    )
    await utils.select_point(is_departure=True, message=message, state=state)


@router.message(states.RouteState.selecting_destination_point)
async def select_destination(message: types.Message, state: FSMContext):
    """User: inputs the destination point. Bot: here's what I have in the DB."""
    logger.info(
        f"User {message.from_user.full_name} TGID {message.from_user.id} entered the "
        f"destination point '{message.text}'. Searching for the point in the DB."
    )
    await utils.select_point(is_departure=False, message=message, state=state)


@router.callback_query(clb.MorePointCunksCallbackFactory.filter())
async def more_buttons_handler(
    callback: types.CallbackQuery,
    callback_data: clb.MorePointCunksCallbackFactory,
    state: FSMContext,
):
    """User: clicks the 'more' button. Bot: here's the next set of points."""
    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} clicked on "
        "the 'More points' inline button. Getting the remaining points from the state "
        "user data and replying to the user."
    )
    user_data: dict = await state.get_data()

    point_chunks: list[list[PointResponsePD]] = user_data["remaining_point_chunks"]
    points: list = point_chunks.pop(0)

    await callback.message.answer(
        msg.MORE_POINT_CHOICES,
        reply_markup=get_point_choice_keyboard(
            points=points,
            is_departure=callback_data.is_departure,
            last_chunk=not point_chunks,
        ),
    )

    logger.debug("Updating the state user data with remanining point chunks.")
    await state.update_data(remaining_point_chunks=point_chunks)
    logger.debug(
        "Amount of remaining chunks in the state user data is "
        f"{len(user_data['remaining_point_chunks'])} chunks."
    )

    await callback.answer()


@router.callback_query(clb.MissingPointCallbackFactory.filter())
async def missing_point_callback(
    callback: types.CallbackQuery,
    callback_data: clb.MissingPointCallbackFactory,
    state: FSMContext,
):
    """User: clicks the 'missing' button. Bot: please start again."""
    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} clicked the "
        "inline button that there are no points of his liking in the choices we gave "
        "them. Replying that they need to input the point differently."
    )
    is_departure: bool = callback_data.is_departure
    await callback.message.answer(msg.MISSING_POINT)
    await callback.answer()

    if is_departure:
        logger.info("Setting state to 'selecting_departure_point'.")
        await state.set_state(states.RouteState.selecting_departure_point)
    else:
        logger.info("Setting state to 'selecting_destination_point'.")
        await state.set_state(states.RouteState.selecting_destination_point)


@router.callback_query(clb.PointsCallbackFactory.filter(F.is_departure == True))  # noqa
async def choose_departure_from_multiple_callback(
    callback: types.CallbackQuery,
    callback_data: clb.PointsCallbackFactory,
    state: FSMContext,
):
    """User: selects the departure from the list. Bot: input the destination point."""
    selected_departure: PointResponsePD = await point_retriever.get_point(
        point_id=callback_data.point_id
    )
    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        f"selected the departure point '{selected_departure.title}'."
        "Replying that they need to input a destinaton point now."
    )
    msg_text: str = msg.SinglePointFound(
        point=selected_departure, is_departure=callback_data.is_departure
    )
    await callback.message.answer(text=f"{msg_text}\n{msg.INPUT_DESTINATION_POINT}")
    await callback.answer()

    logger.debug("UPdating the state data with the selected departure point.")
    await state.update_data(departure_point=selected_departure)

    logger.info("Setting state to 'selecting_destination_point'.")
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
    selected_point: PointResponsePD = await point_retriever.get_point(
        point_id=callback_data.point_id
    )
    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        f"selected the destination point '{selected_point.title}'."
    )
    msg_text = msg.SinglePointFound(
        point=selected_point, is_departure=callback_data.is_departure
    )
    user_data: dict = await state.get_data()
    try:
        departure_point: PointResponsePD = user_data["departure_point"]
    except ValueError as e:
        logger.error(f"Departure point is not found in the state data: {e}")
        callback.message.answer(text=msg.ERROR)
    user: UserORM = await get_user_from_db(telegram_id=callback.from_user.id)

    logger.info(
        f"Getting or creating a route between {departure_point.title} and "
        f"{selected_point.title} in DB."
    )
    route: RouteResponsePD = await route_finder.get_or_create_route(
        departure_point=departure_point, destination_point=selected_point, user=user
    )

    logger.info(
        f"Creating a Timetable object for route {route} for today with threads limit "
        f"{settings.CLOSEST_DEP_LIMIT}."
    )
    timetable_obj = Timetable(
        route=route, limit=settings.CLOSEST_DEP_LIMIT, add_msg_text=str(msg_text)
    )
    logger.info(f"Timetable_object created: {timetable_obj}")

    logger.info("Replying to the user with the timetable.")
    await process_timetable_callback(
        callback=callback,
        state=state,
        timetable_obj=timetable_obj,
    )
