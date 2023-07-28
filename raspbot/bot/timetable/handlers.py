from aiogram import Router, types

from raspbot.bot.constants import callback as clb
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
    timetable = await timetable_obj.msg()
    await callback.message.answer(text=timetable, parse_mode="HTML")
    await callback.answer()
