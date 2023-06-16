import datetime as dt

from raspbot.apicalls.search import TransportTypes, search_between_stations
from raspbot.bot.routes.constants.text import msg
from raspbot.core.exceptions import InvalidTimeFormatError
from raspbot.core.logging import configure_logging
from raspbot.db.routes.schema import RouteResponse

logger = configure_logging(name=__name__)

CLOSEST_DEP_LIMIT = 12
SMALL_REMAINDER = 3
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


def _validate_time(
    raw_time: str, timetable_date: dt.date = dt.date.today()
) -> dt.datetime:
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
            datetime_str = f"{timetable_date} {raw_time}"
            validated_time: dt.datetime = dt.datetime.strptime(
                datetime_str, "%Y-%m-%d %H:%M:%S"
            )
        except ValueError as e:
            raise InvalidTimeFormatError(
                "Время пришло от Яндекса в некорректном формате. Поддерживаются "
                f"2023-05-29T12:48:00.000000 или 12:48:00, а пришло {raw_time}."
                f"Ошибка ValueError: {e}"
            )
    return validated_time


def _get_closest_departures_for_date(
    date: dt.date, timetable_dict: dict, limit: int
) -> list[dt.datetime]:
    """
    Генерирует список ближайших отправлений на указанную дату.

    Принимает на вход:
        - date_ (datetime): Дата, на которую требуется формирование списка ближайших
          отправлений;
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
            departure_time: dt.datetime = _validate_time(
                raw_time=raw_departure_time, timetable_date=date
            )
        except InvalidTimeFormatError as e:
            logger.error(
                f"Время отправления {raw_departure_time} отбраковано "
                f"и не включено в вывод расписания. Причина: {e}."
            )
        current_time = dt.datetime.now(tz=departure_time.tzinfo).strftime(DEP_FORMAT)
        departure_str = departure_time.strftime(DEP_FORMAT)
        if departure_time < dt.datetime.now(tz=departure_time.tzinfo):
            logger.debug(
                f"Отбраковка отправления: Текущее время: {current_time}, "
                f"поезд {departure_str} уже ушёл."
            )
            continue
        if departure_time.date() > date:
            logger.debug(
                f"Отбраковка отправления: Поезд {departure_str} отправляется на "
                "следующий день, поэтому не включается в выборку на указанную дату."
            )
        if len(closest_departures) >= limit:
            break
        closest_departures.append(departure_time)
        logger.debug(f"В список ближайших отправлений добавлено {departure_time}.")
    logger.debug(
        f"Финальное кол-во рейсов в списке на дату {date}: {len(closest_departures)}"
    )
    return closest_departures


def _get_formatted_timetable(
    today_timetable: list[dt.datetime],
    tomorrow_timetable: list[dt.datetime],
    format: str,
) -> str:
    """
    Форматирует отправления (рейсы) и формирует готовое сообщение для Telegram.

    Принимает на вход:
        - today_timetable: Расписание на сегодня, которое необходимо отформатировать,
          в виде списка с объектами datetime.
        - today_timetable: Расписание на завтра, которое необходимо отформатировать,
          в виде списка с объектами datetime.
        - format: Формат времени, к которому необходимо привести отправления.

    Примечания:
        ttbl_dict представляет собой словарь, ключом которого является кортеж из
        булевых значений списков расписаний на сегодня (первая позиция кортежа)
        и на завтра (вторая позиция) соответственно.
        Например, (True, False) следует читать как "в списке отправлений на сегодня
        есть рейсы, а список на завтра пустой. Значит, нужно сформировать для
        пользователя сообщение, в котором будут только рейсы на сегодня".

    Возвращает:
        - str: Отформатированный текст с ближайшими отправлениями, готовый к вставке
          в сообщение Telegram.
    """
    ttbl_dict = {
        (True, False): (
            "{cd}\n{ttbl}\n\n{pb}".format(
                cd=msg.CLOSEST_DEPARTURES,
                ttbl=", ".join([dep.strftime(format) for dep in today_timetable]),
                pb=msg.PRESS_DEPARTURE_BUTTON,
            )
        ),
        (True, True): (
            "{cd}\n{td} {tdttbl}\n{tm} {tmttbl}\n\n{pb}".format(
                cd=msg.CLOSEST_DEPARTURES,
                td=msg.TODAY,
                tdttbl=", ".join([dep.strftime(format) for dep in today_timetable]),
                tm=msg.TOMORROW,
                tmttbl=", ".join([dep.strftime(format) for dep in tomorrow_timetable]),
                pb=msg.PRESS_DEPARTURE_BUTTON,
            )
        ),
        (False, True): (
            "{ot}\n{ttbl}\n\n{pb}".format(
                ot=msg.ONLY_TOMORROW,
                ttbl=", ".join([dep.strftime(format) for dep in tomorrow_timetable]),
                pb=msg.PRESS_DEPARTURE_BUTTON,
            )
        ),
        (False, False): msg.NO_CLOSEST_DEPARTURES,
    }
    return ttbl_dict[(bool(today_timetable), bool(tomorrow_timetable))]


async def get_closest_departures(route: RouteResponse) -> str:
    """
    Генерирует список ближайших отправлений по указанному маршруту.

    Если ближайших рейсов на сегодня нет или осталось очень мало,
    то показывается также несколько рейсов на завтра.

    Принимает на вход:
        - route (RouteResponse): Маршрут в формате RouteResponse.

    Возвращает:
        - str: Отформатированный текст с ближайшими отправлениями, готовый к вставке
          в сообщение Telegram.
    """
    timetable_dict_today: dict = await _get_timetable_dict(
        departure_code=route.departure_point.yandex_code,
        destination_code=route.destination_point.yandex_code,
        date=dt.date.today(),
    )
    closest_departures_today: list[dt.datetime] = _get_closest_departures_for_date(
        date=dt.date.today(),
        timetable_dict=timetable_dict_today,
        limit=CLOSEST_DEP_LIMIT,
    )
    remainder = max(0, CLOSEST_DEP_LIMIT - len(closest_departures_today))
    closest_departures_tomorrow: list[dt.datetime] = []
    last_departure_today: dt.datetime = (
        closest_departures_today[-1] if closest_departures_today else dt.timedelta(0)
    )
    current_time = (
        dt.datetime.now(tz=last_departure_today.tzinfo)
        if closest_departures_today
        else dt.timedelta(0)
    )
    if len(closest_departures_today) < SMALL_REMAINDER or (
        ((last_departure_today - current_time) < dt.timedelta(hours=2)) and remainder
    ):
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        timetable_dict_tomorrow: dict = await _get_timetable_dict(
            departure_code=route.departure_point.yandex_code,
            destination_code=route.destination_point.yandex_code,
            date=tomorrow,
        )
        closest_departures_tomorrow += _get_closest_departures_for_date(
            date=tomorrow,
            timetable_dict=timetable_dict_tomorrow,
            limit=max(remainder, SMALL_REMAINDER),
        )
    formatted_timetable: str = _get_formatted_timetable(
        today_timetable=closest_departures_today,
        tomorrow_timetable=closest_departures_tomorrow,
        format=DEP_FORMAT,
    )

    return formatted_timetable
