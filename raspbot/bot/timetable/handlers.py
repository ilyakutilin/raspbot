import datetime as dt

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.timetable import utils
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.models import Recent, Route
from raspbot.services.deptime import get_uid_by_time
from raspbot.services.other_date import get_timetable_by_date
from raspbot.services.routes import RouteRetriever
from raspbot.services.timetable import Timetable
from raspbot.services.users import update_recent
from raspbot.settings import settings

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


@router.callback_query(clb.GetTimetableCallbackFactory.filter())
async def show_closest_departures_callback(
    callback: types.CallbackQuery,
    callback_data: clb.GetTimetableCallbackFactory,
    state: FSMContext,
):
    """User: selects the route from the list. Bot: here's the timetable.

    Current state: TimetableState:exact_departure_info
    """
    recent: Recent = await update_recent(recent_id=callback_data.recent_id)
    route: Route = await route_retriever.get_route_from_db(route_id=recent.route_id)
    timetable_obj = Timetable(route=route, limit=settings.CLOSEST_DEP_LIMIT)
    await utils.process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


@router.callback_query(clb.DepartureUIDCallbackFactory.filter())
async def show_departure_callback(
    callback: types.CallbackQuery,
    callback_data: clb.DepartureUIDCallbackFactory,
    state: FSMContext,
):
    """User: clicks on departure time. Bot: here's the departure info.

    Current state: TimetableState:exact_departure_info
    """
    timetable_obj: Timetable = await utils.get_timetable_object_from_state(state=state)
    uid: str = callback_data.uid
    await utils.show_dep_info(
        timetable_obj=timetable_obj, uid=uid, message=callback.message
    )
    await callback.answer()


@router.callback_query(F.data == clb.SAME_DEPARTURE)
async def same_departure_callback(callback: types.CallbackQuery, state: FSMContext):
    """User: clicks on the same departure. Bot: here's an error message.

    Current state: TimetableState:exact_departure_info
    """
    await callback.answer(text=msg.SAME_DEPARTURE, show_alert=True)


@router.callback_query(clb.EndOfTheDayTimetableCallbackFactory.filter())
async def show_till_the_end_of_the_day_callback(
    callback: types.CallbackQuery,
    callback_data: clb.EndOfTheDayTimetableCallbackFactory,
    state: FSMContext,
):
    """User: clicks on the button to see full timetable for today. Bot: here you go.

    Current state: TimetableState:exact_departure_info
    """
    route_id: int = callback_data.route_id
    timetable_obj: Timetable = await utils.get_timetable_object_from_state(state=state)
    timetable_obj = timetable_obj.unlimit()
    if timetable_obj.route.id != route_id:
        route: Route = await route_retriever.get_route_from_db(route_id=route_id)
        timetable_obj = Timetable(route=route)
    timetable = await timetable_obj.timetable
    logger.debug(
        "This is what I pass to the process_timetable_callback function after "
        f"unlimiting: {len(timetable)}, last departure: {timetable[-1]}"
    )
    await utils.process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


@router.message(states.TimetableState.exact_departure_info)
async def select_departure_info_by_text(message: types.Message, state: FSMContext):
    """User: types departure time. Bot: here's the departure info.

    Args:
        message: user input
        state: the current FSM state

    Current state: TimetableState:exact_departure_info
    """
    timetable_obj: Timetable = await utils.get_timetable_object_from_state(state=state)
    timetable_obj = timetable_obj.unlimit()
    timetable = await timetable_obj.timetable
    logger.debug(f"timetable_obj has {len(timetable)} elements.")
    try:
        uid: str = await get_uid_by_time(
            user_raw_time_input=message.text, timetable_obj=timetable_obj
        )
        logger.debug(f"uid is {uid}")
        await utils.show_dep_info(
            timetable_obj=timetable_obj, uid=uid, message=message, full_kb=False
        )
    except exc.InvalidDataError as e:
        await message.answer(text=str(e))


@router.callback_query(clb.TomorrowTimetableCallbackFactory.filter())
async def show_tomorrow_timetable_callback(
    callback: types.CallbackQuery,
    callback_data: clb.TomorrowTimetableCallbackFactory,
    state: FSMContext,
):
    """User: clicks on the button to see timetable for tomorrow. Bot: here you go.

    Current state: TimetableState:exact_departure_info
    """
    route_id: int = callback_data.route_id
    route: Route = await route_retriever.get_route_from_db(route_id=route_id)
    tomorrow = dt.date.today() + dt.timedelta(days=1)
    timetable_obj = Timetable(route=route, date=tomorrow)
    await utils.process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


@router.callback_query(clb.OtherDateTimetableCallbackFactory.filter())
async def show_other_date_timetable_callback(
    callback: types.CallbackQuery,
    callback_data: clb.OtherDateTimetableCallbackFactory,
    state: FSMContext,
):
    """User: clicks on button to see timetable for another date. Bot: here you go.

    Current state: TimetableState:exact_departure_info
    """
    route_id: int = callback_data.route_id
    route: Route = await route_retriever.get_route_from_db(route_id=route_id)
    await callback.message.answer(text=msg.TYPE_ARBITRARY_DATE, parse_mode="HTML")
    await callback.answer()
    await state.set_state(states.TimetableState.other_date)
    await state.update_data(route=route)


@router.message(states.TimetableState.other_date)
async def select_date_timetable_by_text(message: types.Message, state: FSMContext):
    """User: types an arbitrary date. Bot: here's the timetable for this date.

    Current state: TimetableState:other_date
    """
    user_data: dict = await state.get_data()
    route: Route = user_data.get("route")
    try:
        timetable_obj = get_timetable_by_date(
            route=route, user_raw_date_input=message.text
        )
        await utils.process_timetable_message(message, state, timetable_obj)
    except exc.InvalidDataError as e:
        await message.answer(text=str(e), parse_mode="HTML")
    except exc.InternalError:
        await message.answer(msg.ERROR)
