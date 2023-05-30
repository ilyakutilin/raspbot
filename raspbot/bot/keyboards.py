from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from raspbot.bot.constants import text
from raspbot.db.stations.models import Station


async def get_station_choice_keyboard(
    statons_from_db: list[Station], is_departure: bool
) -> InlineKeyboardMarkup:
    keyboard = []
    dep_or_dest = 1 if is_departure else 0
    stations_buttons = [
        [
            InlineKeyboardButton(
                f"{station.title}, {station.region.title}",
                callback_data=f"{str(dep_or_dest)}_station_{station.id}",
            )
        ]
        for station in statons_from_db
    ]
    keyboard.extend(stations_buttons)
    keyboard.extend(
        [
            [
                InlineKeyboardButton(
                    text.MY_STATION_IS_NOT_HERE, callback_data="well_then"
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(keyboard)
