from datetime import date, datetime

from raspbot.apicalls.search import search_between_stations
from raspbot.core.exceptions import InvalidTimeFormatError
from raspbot.core.logging import configure_logging

logger = configure_logging(name=__name__)


async def _get_timetable_dict(departure_code: str, destination_code: str) -> dict:
    timetable_dict: dict = await search_between_stations(
        from_=departure_code,
        to=destination_code,
        date=str(date.today()),
        transport_types="suburban",
    )
    logger.info(f"Кол-во рейсов от Яндекса: {len(timetable_dict['segments'])}")
    return timetable_dict


def _validate_time(raw_time: str) -> datetime:
    try:
        validated_time: datetime = datetime.fromisoformat(raw_time)
    except ValueError as e:
        logger.error(
            f"Время пришло от Яндекса не в формате ISO: {raw_time}. "
            f"Ошибка ValueError: {e}"
        )
        try:
            validated_time: datetime = datetime.strptime(raw_time, "%H:%M:%S")
        except ValueError as e:
            raise InvalidTimeFormatError(
                "Время пришло от Яндекса в некорректном формате. Поддерживаются "
                f"2023-05-29T12:48:00.000000 или 12:48:00, а пришло {raw_time}."
                f"Ошибка ValueError: {e}"
            )
    return validated_time


def _get_closest_departures(timetable_dict: dict) -> list[datetime]:
    closest_departures: list[datetime] = []
    for segment in timetable_dict["segments"]:
        raw_departure_time: str = segment["departure"]
        try:
            departure_time: datetime = _validate_time(raw_time=raw_departure_time)
        except InvalidTimeFormatError as e:
            logger.error(
                f"Время отправления {raw_departure_time} отбраковано "
                f"и не включено в вывод расписания. Причина: {e}."
            )
        if departure_time < datetime.now(tz=departure_time.tzinfo):
            logger.debug(
                "Отбраковка отправления: Текущее время "
                f"{datetime.now(tz=departure_time.tzinfo).strftime('%H:%M')} "
                "больше, чем время отправления от Яндекса: "
                f"{departure_time.strftime('%H:%M')}"
            )
            continue
        if len(closest_departures) >= 12:
            break
        closest_departures.append(departure_time)
    logger.info(f"Финальное кол-во рейсов в списке: {len(closest_departures)}")
    return closest_departures


def _get_formatted_timetable(timetable: list[datetime]) -> list[str]:
    formatted_timetable: list[str] = []
    for dep in timetable:
        formatted_timetable.append(dep.strftime("%H:%M"))
    return formatted_timetable


async def search_timetable(departure_code: str, destination_code: str) -> list[str]:
    timetable_dict: dict = await _get_timetable_dict(
        destination_code=destination_code, departure_code=departure_code
    )
    closest_departures: list[datetime] = _get_closest_departures(
        timetable_dict=timetable_dict
    )
    return _get_formatted_timetable(closest_departures)
