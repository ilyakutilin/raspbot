from aiogram import Router, types

from raspbot.bot.constants import callback as clb
from raspbot.bot.timetable.keyboards import get_closest_departures_keyboard
from raspbot.core.logging import configure_logging
from raspbot.db.models import Recent, Route
from raspbot.services.routes import RouteRetriever
from raspbot.services.timetable import ClosestTimetable
from raspbot.services.users import update_recent

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


@router.callback_query(clb.GetTimetableCallbackFactory.filter())
async def show_timetable_callback(
    callback: types.CallbackQuery,
    callback_data: clb.GetTimetableCallbackFactory,
):
    """User: selects the route from the list. Bot: here's the timetable."""
    recent: Recent = await update_recent(recent_id=callback_data.recent_id)
    route: Route = await route_retriever.get_route_from_db(route_id=recent.route_id)
    timetable_obj = await ClosestTimetable(route=route)
    timetable_msg = await timetable_obj.msg()
    timetable = await timetable_obj.get_timetable()
    await callback.message.answer(
        text=timetable_msg,
        reply_markup=get_closest_departures_keyboard(
            departures_list=timetable, route_id=route.id
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(clb.DepartureTimeCallbackFactory.filter())
async def show_departure_callback(
    callback: types.CallbackQuery,
    callback_data: clb.DepartureTimeCallbackFactory,
):
    pass
