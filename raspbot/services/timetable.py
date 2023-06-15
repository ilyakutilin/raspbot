import datetime as dt

from raspbot.apicalls.search import TransportTypes, search_between_stations
from raspbot.core.exceptions import InvalidTimeFormatError
from raspbot.core.logging import configure_logging
from raspbot.db.routes.schema import RouteResponse

logger = configure_logging(name=__name__)

CLOSEST_DEP_LIMIT = 12
DEP_FORMAT = "%H:%M"


async def _get_timetable_dict(
    departure_code: str, destination_code: str, date: dt.date = dt.date.today()
) -> dict:
    """
    Возвращает сырой JSON (в виде словаря) с расписанием от Яндекса.

    Принимает на вход:
        - departure_code (str): Яндекс-код пункта отправления в виде строки,
          пример: "s2000006"
        - destination_code (str): Яндекс-код пункта назначения в виде строки,
          пример: "s9600721"

    Возвращает:
        dict: Полный словарь со всеми рейсами от Яндекса (по-прежнему сырые данные).

    Примечания:
        Лимит пагинации, установленный Яндексом по умолчанию - 100 рейсов.
        В данной функции при формировании запроса в kwargs_dict этот лимит
        не увеличивается; вместо этого формируется несколько словарей, в которых
        постепенно увеличивается оффсет пагинации, и рейсы каждого нового словаря
        добавляются к рейсам основного.
    """
    kwargs_dict = {
        "from_": departure_code,
        "to": destination_code,
        "date": date,
        "transport_types": TransportTypes.SUBURBAN.value,
        "offset": 0,
    }
    timetable_dict: dict = await search_between_stations(**kwargs_dict)
    logger.debug(
        "Элементов в изначальном словаре от Яндекса: "
        f"{len(timetable_dict['segments'])}."
    )
    try:
        total = int(timetable_dict["pagination"]["total"])
        limit = int(timetable_dict["pagination"]["limit"])
        offset = int(timetable_dict["pagination"]["offset"])
        logger.debug(f"Пагинация: total={total}, limit={limit}, offset={offset}")
    except KeyError as e:
        logger.error(
            "Невозможно обработать информацию о пагинации из ответа Яндекса: "
            f"не найдены соответствующие ключи в JSON ({e}). "
            "Возвращаю словарь без изменений."
        )
        logger.info(f"Кол-во рейсов от Яндекса: {len(timetable_dict['segments'])}")
        return timetable_dict
    while total > (limit + offset):
        kwargs_dict["offset"] += limit
        logger.debug(f"Новый оффсет: {kwargs_dict['offset']}")
        next_dict: dict = await search_between_stations(**kwargs_dict)
        logger.debug(
            f"Элементов в словаре с оффсетом {kwargs_dict['offset']}: "
            f"{len(next_dict['segments'])}."
        )
        timetable_dict["segments"] += next_dict["segments"]
        logger.debug(
            "Элементов в обновленном основном словаре: "
            f"{len(timetable_dict['segments'])}"
        )
        offset += 100
    logger.info(f"Кол-во рейсов от Яндекса: {len(timetable_dict['segments'])}")
    return timetable_dict


def _validate_time(raw_time: str) -> dt.datetime:
    """
    Превращает строку времени, пришедшую в сыром ответе, в объект datetime.

    Принимает на вход:
        raw_time (str): Строка времени из сырых данных.
        Допустимые форматы:
            - ISO (пример: 2023-05-29T12:48:00.000000)
            - HH:MM:SS (пример: 12:48:00)

    Вызывает исключения:
        InvalidTimeFormatError: вызывается в случае, если формат времени в строке сырых
        данных не совпадает с ожидаемым и, соответственно, не может быть конвертирован
        в объект datetime.

    Возвращает:
        Объект datetime.
    """
    try:
        validated_time: dt.datetime = dt.datetime.fromisoformat(raw_time)
    except ValueError as e:
        logger.error(
            f"Время пришло от Яндекса не в формате ISO: {raw_time}. "
            f"Ошибка ValueError: {e}"
        )
        try:
            validated_time: dt.datetime = dt.datetime.strptime(raw_time, "%H:%M:%S")
        except ValueError as e:
            raise InvalidTimeFormatError(
                "Время пришло от Яндекса в некорректном формате. Поддерживаются "
                f"2023-05-29T12:48:00.000000 или 12:48:00, а пришло {raw_time}."
                f"Ошибка ValueError: {e}"
            )
    return validated_time


def _get_closest_departures(timetable_dict: dict, limit: int) -> list[dt.datetime]:
    """
    Генерирует список ближайших отправлений.

    Принимает на вход:
        - timetable_dict (dict): Полный словарь (JSON) с сырыми данными,
          скомбинированный с учетом пагинации.
        - limit (int): Лимит количества отправлений.

    Возвращает:
        list[datetime]: Список установленного количества отправлений в формате datetime.
    """

    closest_departures: list[dt.datetime] = []
    for segment in timetable_dict["segments"]:
        raw_departure_time: str = segment["departure"]
        try:
            departure_time: dt.datetime = _validate_time(raw_time=raw_departure_time)
        except InvalidTimeFormatError as e:
            logger.error(
                f"Время отправления {raw_departure_time} отбраковано "
                f"и не включено в вывод расписания. Причина: {e}."
            )
        if departure_time < dt.datetime.now(tz=departure_time.tzinfo):
            logger.debug(
                "Отбраковка отправления: Текущее время "
                f"{dt.datetime.now(tz=departure_time.tzinfo).strftime('%H:%M')}, "
                f"поезд {departure_time.strftime('%H:%M')} уже ушёл."
            )
            continue
        if len(closest_departures) >= limit:
            break
        closest_departures.append(departure_time)
        logger.debug(f"В список ближайших отправлений добавлено {departure_time}.")
    logger.info(f"Финальное кол-во рейсов в списке: {len(closest_departures)}")

    return closest_departures


def _get_formatted_timetable(timetable: list[dt.datetime], format: str) -> list[str]:
    """
    Форматирует отправления в строку.

    Принимает на вход:
        - timetable (list[datetime]): Расписание, которое необходимо отформатировать,
          в виде списка с объектами datetime.
        - format (str): Формат, к которому необходимо привести.

    Возвращает:
        list[str]: Отформатированное расписание в виде списка строк
        установленного формата.
    """
    formatted_timetable: list[str] = []
    for dep in timetable:
        formatted_timetable.append(dep.strftime("%H:%M"))
    return formatted_timetable


async def search_timetable(route: RouteResponse) -> list[str]:
    """
    Ищет расписание между указанными пунктами.

    Принимает на вход:
        - departure_code (str): Яндекс-код пункта отправления в виде строки,
          пример: "s2000006"
        - destination_code (str): Яндекс-код пункта назначения в виде строки,
          пример: "s9600721"

    Возвращает:
        list[str]: Отформатированное расписание в виде списка строк
        установленного формата.
    """
    timetable_dict: dict = await _get_timetable_dict(
        departure_code=route.departure_point.yandex_code,
        destination_code=route.destination_point.yandex_code,
    )
    closest_departures: list[dt.datetime] = _get_closest_departures(
        timetable_dict=timetable_dict, limit=CLOSEST_DEP_LIMIT
    )
    return _get_formatted_timetable(timetable=closest_departures, format=DEP_FORMAT)
