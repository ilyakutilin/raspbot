from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.timetable import keyboards as kb
from raspbot.core.logging import configure_logging
from raspbot.db.models import Recent, Route
from raspbot.db.routes.schema import ThreadResponse
from raspbot.services.routes import RouteRetriever
from raspbot.services.timetable import ClosestTimetable
from raspbot.services.users import update_recent

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


async def process_timetable_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    timetable_obj: ClosestTimetable,
    route_id: int,
    add_msg_text: str | None = None,
):
    timetable_msg = await timetable_obj.msg()
    timetable = await timetable_obj.get_timetable()
    await callback.message.answer(
        text=((add_msg_text + "\n" * 2) if add_msg_text else "") + timetable_msg,
        reply_markup=kb.get_closest_departures_keyboard(
            departures_list=timetable, route_id=route_id
        ),
        parse_mode="HTML",
    )
    await callback.answer()
    await state.update_data(timetable=timetable)
    await state.set_state(states.TimetableState.exact_departure_info)


@router.callback_query(clb.GetTimetableCallbackFactory.filter())
async def show_timetable_callback(
    callback: types.CallbackQuery,
    callback_data: clb.GetTimetableCallbackFactory,
    state: FSMContext,
):
    """User: selects the route from the list. Bot: here's the timetable."""
    recent: Recent = await update_recent(recent_id=callback_data.recent_id)
    route: Route = await route_retriever.get_route_from_db(route_id=recent.route_id)
    timetable_obj = await ClosestTimetable(route=route)
    await process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj, route_id=route.id
    )


@router.callback_query(clb.DepartureUIDCallbackFactory.filter())
async def show_departure_callback(
    callback: types.CallbackQuery,
    callback_data: clb.DepartureUIDCallbackFactory,
    state: FSMContext,
):
    user_data: dict = await state.get_data()
    timetable: list[ThreadResponse] = user_data["timetable"]
    uid: str = callback_data.uid
    route_id: int = callback_data.route_id
    try:
        dep_info: ThreadResponse = next(dep for dep in timetable if dep.uid == uid)
    except StopIteration:
        # TODO: Complete error handling
        logger.error("StopIteration error")
    msg_obj = msg.ThreadInfo(thread=dep_info)
    await callback.message.answer(
        text=str(msg_obj),
        reply_markup=kb.get_separate_departure_keyboard(
            departures_list=timetable, this_departure=dep_info, route_id=route_id
        ),
        parse_mode="HTML",
    )
    await callback.answer()
