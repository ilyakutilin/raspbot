import datetime as dt
from abc import ABC, abstractmethod

from asyncinit import asyncinit
from pydantic import ValidationError

from raspbot.apicalls.search import TransportTypes, search_between_stations
from raspbot.bot.constants import messages as msg
from raspbot.core.exceptions import InvalidTimeFormatError
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import PointTypeEnum, Route
from raspbot.db.routes.schema import RouteResponse, ThreadResponse
from raspbot.settings import settings

logger = configure_logging(name=__name__)


@asyncinit
class Timetable(ABC):
    async def __init__(
        self, route: Route | RouteResponse, date: dt.date = dt.date.today()
    ):
        self.route = route
        self.date = date

    async def _get_timetable_dict(
        self,
        departure_code: str,
        destination_code: str,
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
            "date": self.date,
            "transport_types": TransportTypes.SUBURBAN.value,
            "offset": 0,
        }
        timetable_dict: dict = await search_between_stations(**kwargs_dict)
        logger.debug(
            "Элементов в изначальном словаре от Яндекса: "
            f"{len(timetable_dict['segments'])}."
        )
        try:
            api_total = int(timetable_dict["pagination"]["total"])
            api_limit = int(timetable_dict["pagination"]["limit"])
            api_offset = int(timetable_dict["pagination"]["offset"])
            logger.debug(
                f"Пагинация: total={api_total}, limit={api_limit}, offset={api_offset}"
            )
        except KeyError as e:
            logger.error(
                "Невозможно обработать информацию о пагинации из ответа Яндекса: "
                f"не найдены соответствующие ключи в JSON ({e}). "
                "Возвращаю словарь без изменений."
            )
            logger.info(f"Кол-во рейсов от Яндекса: {len(timetable_dict['segments'])}")
            return timetable_dict
        while api_total > (api_limit + api_offset):
            kwargs_dict["offset"] += api_limit
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
            api_offset += 100
        logger.info(f"Кол-во рейсов от Яндекса: {len(timetable_dict['segments'])}")
        return timetable_dict

    def _validate_time(self, raw_time: str) -> dt.datetime:
        """
        Превращает строку времени, пришедшую в сыром ответе, в объект datetime.

        Принимает на вход:
            raw_time (str): Строка времени из сырых данных.
            Допустимые форматы:
                - ISO (пример: 2023-05-29T12:48:00.000000)
                - HH:MM:SS (пример: 12:48:00)

        Вызывает исключения:
            InvalidTimeFormatError: вызывается в случае, если формат времени в строке
            сырых данных не совпадает с ожидаемым и, соответственно, не может быть
            конвертирован в объект datetime.

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
                datetime_str = f"{self.date} {raw_time}"
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

    def _get_threadresponse_object(
        self,
        segment: dict,
        departure_time: dt.datetime | None = None,
    ) -> ThreadResponse:
        # TODO: Complete docstring
        """
        _summary_

        Args:
            segment (dict): _description_

        Returns:
            ThreadResponse: _description_
        """
        try:
            if not departure_time:
                departure: dt.datetime = self._validate_time(
                    raw_time=segment["departure"]
                )
            arrival: dt.datetime = self._validate_time(raw_time=segment["arrival"])
        except InvalidTimeFormatError:  # TODO: Complete Exception handling
            logger.error("Error")
        except KeyError:  # TODO: Complete Exception handling
            logger.error("Error")
        except ValueError:  # TODO: Complete Exception handling
            logger.error("Error")

        try:
            short_title = segment.get("thread").get("short_title")
            short_from_title = segment.get("from").get("short_title")
            short_to_title = segment.get("to").get("short_title")
            thread = segment["thread"]
            # TODO: Ticket prices
            ticket_price_dict = segment["tickets_info"]["places"][0]["price"]
            ticket_price = float(
                f"{ticket_price_dict['whole']}.{ticket_price_dict['cents']}"
            )

            threadresponse = ThreadResponse(
                uid=thread["uid"],
                number=thread["number"],
                title=short_title if short_title else thread["title"],
                carrier=thread["carrier"]["title"],
                transport_subtype=thread["transport_subtype"]["title"],
                express_type=thread["express_type"],
                from_=short_from_title
                if short_from_title
                else segment["from"]["title"],
                to=short_to_title if short_to_title else segment["to"]["title"],
                departure=departure_time if departure_time else departure,
                arrival=arrival,
                date=self.date,
                stops=segment["stops"],
                departure_platform=segment["departure_platform"],
                arrival_platform=segment["arrival_platform"],
                departure_terminal=segment["departure_terminal"],
                arrival_terminal=segment["arrival_terminal"],
                duration=segment["duration"],
                ticket_price=ticket_price,
            )
            logger.debug(f"Threadresponse: {threadresponse}")
            return threadresponse
        except KeyError:  # TODO: Complete Exception handling
            logger.error("Error")
        except ValidationError as e:  # TODO: Complete Exception handling
            logger.error(f"ValidationError: {e}")

    @log(logger)
    def format_thread_list(self, thread_list: list[ThreadResponse]) -> str:
        simple_threads = "\n".join([dep.message_with_route for dep in thread_list])
        one_from_station = all(dep.from_ == thread_list[0].from_ for dep in thread_list)
        one_to_station = all(dep.to == thread_list[0].to for dep in thread_list)
        formatted_unified = msg.FormattedUnifiedThreadList(thread_list=thread_list)
        formatted_different = msg.FormattedDifferentThreadList(thread_list=thread_list)
        match (
            self.route.departure_point.point_type,
            self.route.destination_point.point_type,
        ):
            case PointTypeEnum.station, PointTypeEnum.station:
                return simple_threads
            case PointTypeEnum.station, PointTypeEnum.settlement:
                if one_to_station:
                    return formatted_unified.station_to_settlement()
                return formatted_different.station_to_settlement()
            case PointTypeEnum.settlement, PointTypeEnum.station:
                if one_from_station:
                    return formatted_unified.settlement_to_station()
                return formatted_different.settlement_to_station()
            case PointTypeEnum.settlement, PointTypeEnum.settlement:
                if one_from_station and one_to_station:
                    return formatted_unified.settlement_to_settlement()
                if one_from_station and not one_to_station:
                    return formatted_different.settlement_one_to_settlement_diff()
                if one_to_station and not one_from_station:
                    return formatted_different.settlement_diff_to_settlement_one()
                return formatted_different.settlement_diff_to_settlement_diff()
        return "\n".join([dep.str_time_with_express_type for dep in thread_list])

    @property
    @abstractmethod
    async def timetable(self) -> list[ThreadResponse]:
        pass

    @property
    @abstractmethod
    async def length(self) -> list[ThreadResponse]:
        pass

    @property
    @abstractmethod
    async def msg(self) -> str:
        pass


@asyncinit
class TodayTimetable(Timetable):
    # TODO: Complete the docstring
    """_summary_

    Args:
        - limit (int): Лимит количества отправлений.
          Задаётся если нужно вывести расписание ближайших отправлений.

    """

    async def __init__(self, route: Route | RouteResponse, limit: int | None = None):
        await super().__init__(route)
        self.limit = limit

    async def _get_timetable_till_the_end_of_the_day(self) -> list[ThreadResponse]:
        # TODO: Complete docstring
        """_summary_

        Returns:
            list[ThreadResponse]: _description_
        """
        today = dt.date.today()
        timetable_dict: dict = await self._get_timetable_dict(
            departure_code=self.route.departure_point.yandex_code,
            destination_code=self.route.destination_point.yandex_code,
        )
        today_departures: list[ThreadResponse] = []
        for segment in timetable_dict["segments"]:
            raw_departure_time: str = segment["departure"]
            try:
                departure_time: dt.datetime = self._validate_time(
                    raw_time=raw_departure_time
                )
            except InvalidTimeFormatError as e:
                logger.error(
                    f"Время отправления {raw_departure_time} отбраковано "
                    f"и не включено в вывод расписания. Причина: {e}."
                )
            current_time = dt.datetime.now(tz=departure_time.tzinfo).strftime(
                settings.DEP_FORMAT
            )
            departure_str = departure_time.strftime(settings.DEP_FORMAT)
            if departure_time < dt.datetime.now(tz=departure_time.tzinfo):
                logger.debug(
                    f"Отбраковка отправления: Текущее время: {current_time}, "
                    f"поезд {departure_str} уже ушёл."
                )
                continue
            threadresponse = self._get_threadresponse_object(
                segment=segment,
                departure_time=departure_time,
            )
            today_departures.append(threadresponse)
            logger.debug(
                f"В список сегодняшних отправлений добавлено {threadresponse.str_time},"
                f" объект типа {threadresponse.__class__.__name__}"
            )
        logger.debug(
            f"Финальное кол-во рейсов в списке на сегодня, {today}: "
            f"{len(today_departures)}"
        )
        return today_departures

    @property
    async def length(self) -> int:
        timetable = await self._get_timetable_till_the_end_of_the_day()
        return len(timetable)

    @property
    async def timetable(self) -> list[ThreadResponse]:
        """
        Генерирует список отправлений на сегодня.

        Принимает на вход:
            - limit (int): Лимит количества отправлений.
              Задаётся если нужно вывести расписание ближайших отправлений.

        Возвращает:
            list[ThreadResponse]: Список установленного количества отправлений
            в формате ThreadResponse.
        """
        if self.limit:
            timetable = await self._get_timetable_till_the_end_of_the_day()
            return timetable[: self.limit]
        return await self._get_timetable_till_the_end_of_the_day()

    @property
    async def msg(self) -> str:
        """
        Генерирует список ближайших отправлений по указанному маршруту для сообщения.

        Возвращает:
            - str: Отформатированный текст с отправлениями, готовый к вставке
            в сообщение Telegram.
        """
        today_departures = await self.timetable
        thread_list: str = self.format_thread_list(today_departures)
        if not today_departures:
            return msg.NO_TODAY_DEPARTURES.format(route=str(self.route))
        length = await self.length
        message_part_one = (
            msg.CLOSEST_DEPARTURES
            if self.limit and length > self.limit
            else msg.TODAY_DEPARTURES
        )
        message_part_two = (
            msg.PRESS_DEPARTURE_BUTTON
            if self.limit or length <= settings.INLINE_DEPARTURES_QTY
            else msg.PRESS_DEPARTURE_BUTTON_OR_TYPE
        )
        return (
            f"{message_part_one.format(route=str(self.route))}\n\n{thread_list}"
            f"\n\n{message_part_two}"
        )
