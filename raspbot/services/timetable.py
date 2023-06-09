from datetime import date, datetime

from raspbot.apicalls.search import search_between_stations
from raspbot.core.logging import configure_logging

logger = configure_logging(name=__name__)


async def search_timetable(departure_code: str, destination_code: str):
    timetable_dict: dict = await search_between_stations(
        from_=departure_code,
        to=destination_code,
        date=str(date.today()),
    )
    logger.info(f"Кол-во рейсов от Яндекса: {len(timetable_dict['segments'])}")
    closest_departures: list[datetime] = []
    for segment in timetable_dict["segments"]:
        departure: str = segment["departure"]
        try:
            departure_time: datetime = datetime.fromisoformat(departure)
        except ValueError as e:
            logger.error(e)
            try:
                departure_time: datetime = datetime.strptime(departure, "%H:%M:%S")
            except ValueError as e:
                logger.error(e)
                print(
                    "Время пришло от Яндекса в некорректном формате. Поддерживаются "
                    f"2023-05-29T12:48:00.000000 или 12:48:00, а пришло {departure}."
                )
        if (
            departure_time < datetime.now(tz=departure_time.tzinfo)
            or len(closest_departures) > 10
        ):
            logger.info(
                "Отбраковка: Текущее время: "
                f"{datetime.now(tz=departure_time.tzinfo)},"
                f"Кол-во рейсов в списке: {len(closest_departures)},"
                "Время отправления от Яндекса: "
                f"{departure_time.strftime('%H:%M')}"
            )
            continue
        closest_departures.append(departure_time)
    logger.info(f"Финальное кол-во рейсов в списке: {len(closest_departures)}")
    timetable: list[str] = []
    for dep in closest_departures:
        timetable.append(dep.strftime("%H:%M"))
    return timetable
