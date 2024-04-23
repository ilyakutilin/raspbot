import asyncio
import datetime
import json
from enum import Enum
from typing import Mapping

from raspbot.apicalls.base import get_response
from raspbot.core.exceptions import (
    InvalidDataError,
    InvalidDateError,
    InvalidValueError,
)
from raspbot.core.logging import configure_logging
from raspbot.settings import settings as s

logger = configure_logging(name=__name__)


class Args(Enum):
    """Arguments for the main function search_between_stations."""

    @classmethod
    def list(cls):
        """Returns the list of arguments."""
        return list(map(lambda c: c.value, cls))


class Format(Args):
    """Format choices."""

    JSON = "json"
    XML = "xml"


class Lang(Args):
    """Language choices."""

    RU = "ru_RU"
    UA = "uk_UA"


class TransportTypes(Args):
    """Transport types choices."""

    PLANE = "plane"
    TRAIN = "train"
    SUBURBAN = "suburban"
    BUS = "bus"
    WATER = "water"
    HELICOPTER = "helicopter"


def _validate_arg(
    key: str,
    value: object,
) -> tuple[str]:
    """
    Валидирует компонент запроса (аргумент основной функции search_between_stations).

    Принимает на вход:
        - value (object): значение аргумента;
        - key_name (str): имя аргумента.

    Вызывает исключения:
        - InvalidDateError: Дата в прошлом.
          Поиск может быть только начиная с сегодняшнего дня.
        - InvalidValueError: Значения format, lang и transport_types должны быть выбраны
          из предустановленного списка.
    """
    enums = {"format": Format, "lang": Lang, "transport_types": TransportTypes}
    if key == "date":
        if value < datetime.date.today():
            raise InvalidDateError("Дата поиска не может быть в прошлом.")
    if key in enums.keys() and not isinstance(value, Enum):
        allowed_values = enums[key].list()
        if value not in allowed_values:
            raise InvalidValueError(
                f"Значение {key} должно быть одним из: {allowed_values}"
            )
    # В key_str нужно убрать нижнее подчёркивание из поля "from_"
    key_str = str(key).rstrip("_")
    value_str = str(value)
    logger.debug(f"key_str = {key_str}, value_str = {value_str}")
    return key_str, value_str


async def search_between_stations(
    from_: str,
    to: str,
    date: datetime.datetime | None = None,
    format: str | Format | None = None,
    lang: str | Lang | None = None,
    transport_types: str | TransportTypes | None = None,
    offset: int | None = None,
    limit: int | None = None,
    add_days_mask: bool | None = None,
    result_timezone: str | None = None,
    transfers: bool | None = None,
) -> Mapping:
    """
    Поиск расписания между станциями / городами.

    Принимает на вход:
        - from_ (строка): Яндекс-код пункта отправления в виде строки,
          пример: "s2000006";
        - to (строка): Яндекс-код пункта назначения в виде строки,
          пример: "s9600721";
        - date: дата в формате ISO 8601 (напр. YYYY-MM-DD), по умолчанию -
          только прямые рейсы на все даты;
        - format: строка или Enum (класс Format): json или xml;
        - lang: строка или Enum (класс Lang), код языка по ISO 639: русский "ru_RU"
          или украинский "uk_UA", по умолчанию - русский;
        - transport_types: строка или Enum (класс TransportTypes): plane, train,
          suburban, bus, water, helicopter, по умолчанию - поиск по всем типам;
        - offset: int, смещение относительно первого результата поиска,
          по умолчанию 0;
        - limit: int, максимальное количество результатов поиска в ответе,
          по умолчанию 100;
        - add_days_mask: bool, календарь хождения для каждой нитки,
          по умолчанию False;
        - result_timezone: строка, часовой пояс, для которого следует указывать даты и
          времена в ответе. По умолчанию - часовой пояс соответствующей станции;
        - transfers: bool, признак, разрешающий добавить к результатам поиска маршруты
          с пересадками. По умолчанию - False.

    Возвращает:
        Словарь с распианием между указанными пунктами в "сыром" виде.
    """
    # Получаем локальные переменные функции, т.е. на данном этапе все переданные ей
    # аргументы. Нужно получить их до объявления других переменных.
    args = locals().items()
    url_components = [f"{s.SEARCH_ENDPOINT}?"]
    for key, value in args:
        logger.debug(f"Аргумент {key}, значение {value}.")
        if value is not None:
            logger.debug(
                f"Поскольку значение {value} не None, приступаем к его валидации."
            )
            try:
                key_str, value_str = _validate_arg(key=key, value=value)
            except InvalidDataError as e:
                logger.error(
                    f"Значение '{value}' аргумента {key}, переданное в функцию "
                    f"search_between_stations, некорректно: {e}"
                )
            logger.debug(
                f"URL на данном этапе: {''.join([item for item in url_components])}; "
                f"добавляем к нему это: {key_str}={value_str}&"
            )
            url_components.append(f"{key_str}={value_str}&")
    url = "".join([item for item in url_components]).rstrip("&")
    logger.info(f"Сформирован URL для поиска между пунктами: {url}")
    response = await get_response(endpoint=url, headers=s.headers)
    return response


if __name__ == "__main__":
    tt = asyncio.run(
        search_between_stations(
            from_="s9601728", to="s2000006", date=datetime.date.today(), offset=100
        )
    )
    with open(file="timetable.json", mode="w", encoding="UTF-8") as file:
        json.dump(obj=tt, fp=file, ensure_ascii=False, indent=2)
