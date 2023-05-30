import json
from datetime import datetime

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from raspbot.apicalls.search import search_between_stations
from raspbot.bot.constants import states, text
from raspbot.bot.keyboards import get_station_choice_keyboard
from raspbot.core.logging import configure_logging
from raspbot.db.stations.crud import CRUDStations
from raspbot.db.stations.models import Station

logger = configure_logging(name=__name__)

crud = CRUDStations()

route: dict[str, Station | None] = {
    "departure_station": None,
    "destination_station": None,
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        text=f"{text.GREETING}\n\n{text.INPUT_DEPARTURE_STATION}",
    )
    return states.DEPARTURE_STATION


async def departure_station(update: Update, context: ContextTypes.DEFAULT_TYPE):
    departure_station: str = " ".join(update.message.text.split())
    stations_from_db: list[Station] = await crud.get_stations_by_title(
        title=departure_station
    )
    if not stations_from_db:
        await update.message.reply_text(text=text.STATION_NOT_FOUND)
        return states.DEPARTURE_STATION
    if len(stations_from_db) > 1:
        reply_markup = await get_station_choice_keyboard(
            statons_from_db=stations_from_db, is_departure=True
        )
        await update.message.reply_text(
            text=text.MULTIPLE_STATIONS_FOUND, reply_markup=reply_markup
        )
        return states.CHOOSE_STATION_FROM_MULTIPLE
    route["departure_station"]: Station = stations_from_db[0]
    await update.message.reply_text(text=text.INPUT_DESTINATION_STATION)
    return states.DESTINATION_STATION


async def choose_station_from_multiple(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    station_id = int(update.callback_query.data.split("_")[2])
    station: Station = await crud.get_or_none(station_id)
    is_departure = bool(int(update.callback_query.data.split("_")[0]))
    if station:
        key = "departure_station" if is_departure else "destination_station"
        route[key] = station
    if is_departure:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text.INPUT_DESTINATION_STATION
        )
        return states.DESTINATION_STATION
    return states.GET_TIMETABLE_BETWEEN_STATIONS


async def destination_station(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    destination_station: str = " ".join(update.message.text.split())
    stations_from_db: list[Station] = await crud.get_stations_by_title(
        title=destination_station
    )
    if not stations_from_db:
        await update.message.reply_text(text=text.STATION_NOT_FOUND)
        return states.DESTINATION_STATION
    if len(stations_from_db) > 1:
        reply_markup = await get_station_choice_keyboard(
            statons_from_db=stations_from_db, is_departure=False
        )
        await update.message.reply_text(
            text=text.MULTIPLE_STATIONS_FOUND, reply_markup=reply_markup
        )
        return states.CHOOSE_STATION_FROM_MULTIPLE
    route["destination_station"]: Station = stations_from_db[0]
    logger.info("I am here")
    await update.message.reply_text(
        text=text.SEARCHING_FOR_TIMETABLE.format(
            departure_station=route["departure_station"].title,
            destination_station=route["destination_station"].title,
        )
    )
    return states.GET_TIMETABLE_BETWEEN_STATIONS


async def get_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    departure_station_code: str = route["departure_station"].yandex_code
    logger.info(f"Departure station code {departure_station_code}")
    destination_station_code: str = route["destination_station"].yandex_code
    logger.info(f"Destination station code {destination_station_code}")
    timetable_dict = await search_between_stations(
        from_=departure_station_code, to=destination_station_code, date=datetime.today()
    )
    logger.info(
        "Timetable dict is ready. It contains "
        f"{len(timetable_dict['segments'])} segments"
    )
    closest_departures: list[datetime] = []
    for segment in timetable_dict["segments"][:10]:
        departure: str = segment["departure"]
        try:
            departure_time: datetime = datetime.fromisoformat(departure)
        except ValueError as e:
            logger.error(e)
            departure_time: datetime = datetime.strptime(departure, "%H:%M:%S")
        closest_departures.append(departure_time)
    timetable: list[str] = []
    for dep in closest_departures:
        timetable.append(dep.strftime("%H:%M"))
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=", ".join(timetable),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Bye! I hope we can talk again some day.")
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        states.DEPARTURE_STATION: [MessageHandler(filters.TEXT, departure_station)],
        states.DESTINATION_STATION: [MessageHandler(filters.TEXT, destination_station)],
        states.CHOOSE_STATION_FROM_MULTIPLE: [
            MessageHandler(filters.TEXT, choose_station_from_multiple)
        ],
        states.GET_TIMETABLE_BETWEEN_STATIONS: [
            MessageHandler(filters.TEXT, get_timetable)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
