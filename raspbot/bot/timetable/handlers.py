from aiogram import Router, types

from raspbot.bot.constants import callback as clb
from raspbot.core.logging import configure_logging
from raspbot.db.routes.models import Route
from raspbot.services.routes import RouteRetriever
from raspbot.services.timetable import get_closest_departures

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


@router.callback_query(clb.RecentCallbackFactory.filter())
async def show_recent_timetable_callback(
    callback: types.CallbackQuery,
    callback_data: clb.RecentCallbackFactory,
):
    """User: selects the route from the list. Bot: here's the timetable."""
    route: Route = await route_retriever.get_route_from_db(
        route_id=callback_data.route_id
    )
    timetable: str = await get_closest_departures(route=route)
    await callback.message.answer(text=timetable)
    await callback.answer()
