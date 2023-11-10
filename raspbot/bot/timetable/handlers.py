from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.timetable import keyboards as kb
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.models import Recent, Route
from raspbot.db.routes.schema import ThreadResponse
from raspbot.services.deptime import get_uid_by_time
from raspbot.services.routes import RouteRetriever
from raspbot.services.timetable import Timetable, TodayTimetable
from raspbot.services.users import update_recent
from raspbot.settings import settings

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


async def process_timetable_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    timetable_obj: Timetable,
    add_msg_text: str | None = None,
):
    timetable_obj_msg = await timetable_obj.msg
    logger.debug(
        "text: " f"{(add_msg_text if add_msg_text else '') + timetable_obj_msg}"
    )
    await callback.message.answer(
        text=((add_msg_text + "\n" * 2) if add_msg_text else "") + timetable_obj_msg,
        reply_markup=await kb.get_closest_departures_keyboard(
            timetable_obj=timetable_obj
        ),
        parse_mode="HTML",
    )
    await callback.answer()
    await state.update_data(timetable_obj=timetable_obj)
    await state.set_state(states.TimetableState.exact_departure_info)


@router.callback_query(clb.GetTimetableCallbackFactory.filter())
async def show_closest_departures_callback(
    callback: types.CallbackQuery,
    callback_data: clb.GetTimetableCallbackFactory,
    state: FSMContext,
):
    """User: selects the route from the list. Bot: here's the timetable."""
    recent: Recent = await update_recent(recent_id=callback_data.recent_id)
    route: Route = await route_retriever.get_route_from_db(route_id=recent.route_id)
    timetable_obj = TodayTimetable(route=route, limit=settings.CLOSEST_DEP_LIMIT)
    await process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


async def get_timetable_object_from_state(state: FSMContext) -> Timetable | None:
    """Get the timetable object from the FSM Context state dictionary.

    Args:
        state: current FSMContext

    Returns:

    """
    user_data: dict = await state.get_data()
    try:
        timetable_obj: Timetable = user_data["timetable_obj"]
    except TypeError as e:
        logger.error(f"user_data is not a dict: {e}")
        return None
    except KeyError:
        logger.error("There is no 'timetable_obj' key in the user_data dict.")
        return None
    return timetable_obj


async def show_dep_info(
    timetable_obj: Timetable, uid: str, message: types.Message
) -> None:
    timetable = await timetable_obj.timetable
    try:
        dep_info: ThreadResponse = next(dep for dep in timetable if dep.uid == uid)
    except StopIteration:
        # TODO: Complete error handling
        logger.error("StopIteration error")
    msg_obj = msg.ThreadInfo(thread=dep_info)
    await message.answer(
        text=str(msg_obj),
        reply_markup=await kb.get_separate_departure_keyboard(
            timetable_obj=timetable_obj,
            this_departure=dep_info,
        ),
        parse_mode="HTML",
    )


@router.callback_query(clb.DepartureUIDCallbackFactory.filter())
async def show_departure_callback(
    callback: types.CallbackQuery,
    callback_data: clb.DepartureUIDCallbackFactory,
    state: FSMContext,
):
    timetable_obj: Timetable = await get_timetable_object_from_state(state=state)
    uid: str = callback_data.uid
    await show_dep_info(timetable_obj=timetable_obj, uid=uid, message=callback.message)
    await callback.answer()


@router.callback_query(Text(clb.SAME_DEPARTURE))
async def same_departure_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(text=msg.SAME_DEPARTURE, show_alert=True)


@router.callback_query(clb.EndOfTheDayTimetableCallbackFactory.filter())
async def show_till_the_end_of_the_day_callback(
    callback: types.CallbackQuery,
    callback_data: clb.EndOfTheDayTimetableCallbackFactory,
    state: FSMContext,
):
    route_id: int = callback_data.route_id
    timetable_obj: Timetable = await get_timetable_object_from_state(state=state)
    timetable_obj = timetable_obj.unlimit()
    if timetable_obj.route.id != route_id:
        route: Route = await route_retriever.get_route_from_db(route_id=route_id)
        timetable_obj = TodayTimetable(route=route)
    timetable = await timetable_obj.timetable
    logger.debug(
        "This is what I pass to the process_timetable_callback function after "
        f"unlimiting: {len(timetable)}, last departure: {timetable[-1]}"
    )
    await process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


@router.message(states.TimetableState.exact_departure_info)
async def select_departure_info_by_text(message: types.Message, state: FSMContext):
    """User: types departure time. Bot: here's the departure info.

    Args:
        message: user input
        state: the current FSM state
    """
    timetable_obj: Timetable = await get_timetable_object_from_state(state=state)
    timetable = await timetable_obj.timetable
    logger.debug(f"timetable_obj has {len(timetable)} elements.")
    try:
        uid: str = await get_uid_by_time(
            user_raw_time_input=message.text, timetable_obj=timetable_obj
        )
        logger.debug(f"uid is {uid}")
        await show_dep_info(timetable_obj=timetable_obj, uid=uid, message=message)
    except exc.InvalidDataError as e:
        await message.answer(text=str(e))
