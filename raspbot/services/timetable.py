import datetime as dt
from typing import Self

from async_property import async_cached_property, async_property
from pydantic import ValidationError

from raspbot.apicalls.search import TransportTypes, search_between_stations
from raspbot.bot.constants import messages as msg
from raspbot.core.exceptions import InvalidTimeFormatError
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import PointTypeEnum, RouteORM
from raspbot.db.routes.schema import RouteResponsePD, ThreadResponsePD
from raspbot.services.pretty_day import prettify_day
from raspbot.settings import settings

logger = configure_logging(name=__name__)


class Timetable:
    """A class representing a timetable."""

    def __init__(
        self,
        route: RouteORM | RouteResponsePD,
        date: dt.date = dt.date.today(),
        limit: int | None = None,
        add_msg_text: str | None = None,
    ):
        """Initializes a Timetable class instance."""
        self.route = route
        self.date = date
        self.limit = limit
        self.add_msg_text = (add_msg_text + "\n" * 2) if add_msg_text else ""

    @log(logger)
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
            "Number of elements in raw dict from API: "
            f"{len(timetable_dict['segments'])}."
        )
        try:
            api_total = int(timetable_dict["pagination"]["total"])
            api_limit = int(timetable_dict["pagination"]["limit"])
            api_offset = int(timetable_dict["pagination"]["offset"])
            logger.debug(
                f"Pagination: total={api_total}, limit={api_limit}, offset={api_offset}"
            )
        except KeyError as e:
            logger.error(
                f"API pagination info handling failed: no keys in JSON ({e}). "
                "Returning unchanged dict."
            )
            logger.info(
                f"Number of threads from API: {len(timetable_dict['segments'])}"
            )
            return timetable_dict
        while api_total > (api_limit + api_offset):
            kwargs_dict["offset"] += api_limit
            logger.debug(f"New offset: {kwargs_dict['offset']}")
            next_dict: dict = await search_between_stations(**kwargs_dict)
            logger.debug(
                f"Number of elements in a dict with offset {kwargs_dict['offset']}: "
                f"{len(next_dict['segments'])}."
            )
            timetable_dict["segments"] += next_dict["segments"]
            logger.debug(
                "Number of elements in renewed main dict: "
                f"{len(timetable_dict['segments'])}"
            )
            api_offset += 100
        logger.info(f"Number of threads from API: {len(timetable_dict['segments'])}")
        return timetable_dict

    @log(logger)
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
                f"Time from API is not in ISO format: {raw_time}. ValueError: {e}"
            )
            try:
                datetime_str = f"{self.date} {raw_time}"
                validated_time: dt.datetime = dt.datetime.strptime(
                    datetime_str, "%Y-%m-%d %H:%M:%S"
                )
            except ValueError as e:
                raise InvalidTimeFormatError(
                    "Time from API is in an incorrect format. "
                    "2023-05-29T12:48:00.000000 or 12:48:00 are supported. Got "
                    f"{raw_time}. ValueError: {e}"
                )
        return validated_time

    @log(logger)
    def _get_threadresponse_object(
        self,
        segment: dict,
        departure_time: dt.datetime | None = None,
    ) -> ThreadResponsePD:
        # TODO: Complete docstring
        # """
        # _summary_

        # Args:
        #     segment (dict): _description_

        # Returns:
        #     ThreadResponse: _description_
        # """
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
            ticket_price_dict = segment["tickets_info"]["places"][0]["price"]
            ticket_price = float(
                f"{ticket_price_dict['whole']}.{ticket_price_dict['cents']}"
            )

            threadresponse = ThreadResponsePD(
                uid=thread["uid"],
                number=thread["number"],
                title=short_title if short_title else thread["title"],
                carrier=thread["carrier"]["title"],
                transport_subtype=thread["transport_subtype"]["title"],
                express_type=thread["express_type"],
                from_=(
                    short_from_title if short_from_title else segment["from"]["title"]
                ),
                to=(short_to_title if short_to_title else segment["to"]["title"]),
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
    def format_thread_list(
        self,
        thread_list: list[ThreadResponsePD],
        max_length: int = settings.MAX_TG_MSG_LENGTH,
        max_threads_for_long_fmt: int = settings.MAX_THREADS_FOR_LONG_FMT,
    ) -> tuple[str]:
        """Formats the thread list."""
        simple_threads_short = (
            ", ".join([dep.str_time_with_express_type for dep in thread_list]),
        )
        simple_threads = ("\n".join([dep.message_with_route for dep in thread_list]),)
        formatted_unified = msg.FormattedUnifiedThreadList(
            thread_list=thread_list, max_length=max_length
        )
        formatted_different = msg.FormattedDifferentThreadList(
            thread_list=thread_list, max_length=max_length
        )
        one_from_station: bool = all(
            dep.from_ == thread_list[0].from_ for dep in thread_list
        )
        one_to_station: bool = all(dep.to == thread_list[0].to for dep in thread_list)

        match (
            self.route.departure_point.point_type,
            self.route.destination_point.point_type,
        ):
            case PointTypeEnum.station, PointTypeEnum.station:
                return (
                    simple_threads
                    if len(thread_list) <= max_threads_for_long_fmt
                    else simple_threads_short
                )
            case PointTypeEnum.station, PointTypeEnum.settlement:
                formatted = formatted_unified if one_to_station else formatted_different
                return formatted.station_to_settlement()
            case PointTypeEnum.settlement, PointTypeEnum.station:
                formatted = (
                    formatted_unified if one_from_station else formatted_different
                )
                return formatted.settlement_to_station()
            case PointTypeEnum.settlement, PointTypeEnum.settlement:
                if one_from_station and one_to_station:
                    return formatted_unified.settlement_to_settlement()
                if one_from_station and not one_to_station:
                    return formatted_different.settlement_one_to_settlement_diff()
                if one_to_station and not one_from_station:
                    return formatted_different.settlement_diff_to_settlement_one()
                return formatted_different.settlement_diff_to_settlement_diff()
        return ("\n".join([dep.str_time_with_express_type for dep in thread_list]),)

    @async_cached_property
    async def _full_timetable(self) -> list[ThreadResponsePD]:
        # TODO: Complete docstring
        # """_summary_

        # Returns:
        #     list[ThreadResponse]: _description_
        # """
        timetable_dict: dict = await self._get_timetable_dict(
            departure_code=self.route.departure_point.yandex_code,
            destination_code=self.route.destination_point.yandex_code,
        )
        departures: list[ThreadResponsePD] = []
        for segment in timetable_dict["segments"]:
            raw_departure_time: str = segment["departure"]
            try:
                departure_time: dt.datetime = self._validate_time(
                    raw_time=raw_departure_time
                )
            except InvalidTimeFormatError as e:
                logger.error(
                    f"Departure {raw_departure_time} is rejected "
                    f"and not included in a timetable. Reason: {e}."
                )
            current_time = dt.datetime.now(tz=departure_time.tzinfo).strftime(
                settings.DEP_FORMAT
            )
            departure_str = departure_time.strftime(settings.DEP_FORMAT)
            if departure_time < dt.datetime.now(tz=departure_time.tzinfo):
                logger.debug(
                    f"Departure is rejected: Current time: {current_time}, "
                    f"train {departure_str} has already left."
                )
                continue
            threadresponse = self._get_threadresponse_object(
                segment=segment,
                departure_time=departure_time,
            )
            departures.append(threadresponse)
            logger.debug(
                f"{threadresponse.str_time} has been included in the list of today's "
                f"departures, object of type {threadresponse.__class__.__name__}"
            )
        logger.debug(
            f"Final amount of departures in a timetable for {self.date}: "
            f"{len(departures)}"
        )
        return departures

    @async_property
    async def timetable(self) -> list[ThreadResponsePD]:
        """Gets the timetable in the form of a list of ThreadResponse objects."""
        if self.limit:
            timetable = await self._full_timetable
            return timetable[: self.limit]
        return await self._full_timetable

    @async_cached_property
    async def length(self) -> int:
        """Length of the timetable as the number of ThreadResponse objects."""
        timetable = await self._full_timetable
        return len(timetable)

    @log(logger)
    def _get_message_part_one(self, length: int, route: str) -> str:
        """Returns the first part of the message."""
        if self.date == dt.date.today():
            message_part_one = (
                msg.CLOSEST_DEPARTURES
                if self.limit and length > self.limit
                else msg.TODAY_DEPARTURES.format(route=route)
            )
        else:
            message_part_one = msg.DATE_DEPARTURES.format(
                route=route, date=prettify_day(date=self.date)
            )
        return message_part_one

    @log(logger)
    def _get_message_part_two(self, length: int) -> str:
        """Returns the second part of the message."""
        if self.limit or length <= settings.CLOSEST_DEP_LIMIT:
            return msg.PRESS_DEPARTURE_BUTTON
        if self.date != dt.date.today():
            return msg.TYPE_DEPARTURE
        return msg.PRESS_DEPARTURE_BUTTON_OR_TYPE

    @async_property
    async def msg(self) -> tuple[str]:
        """
        Генерирует кортеж готовых сообщений для Telegram.

        Возвращает:
            - Кортеж, состоящий из сообщений с отформатированным текстом
            с отправлениями, готовыми к отправке.
            Возвращается именно кортеж, поскольку Telegram не позволяет отправлять
            сообщения длиннее определенного лимита. Соотвественно, кортеж представляет
            собой общее отформатированное раписание, разбитое на части с учетом
            этого лимита.
        """
        logger.debug("Generating a tuple of messages to be replied to the user.")
        route = str(self.route)
        timetable = await self.timetable
        if not self.timetable:
            return msg.NO_TODAY_DEPARTURES.format(route=route)
        length = await self.length
        message_part_one = self._get_message_part_one(length=length, route=route)
        message_part_two = self._get_message_part_two(length=length)
        pre_thread_msg_length = len(
            f"{self.add_msg_text}"
            f"{message_part_one.format(route=str(self.route))}\n\n"
            f"\n\n{message_part_two}\n\n{msg.CONT_NEXT_MSG}"
        )
        thread_list: tuple[str] = self.format_thread_list(
            thread_list=timetable,
            max_length=settings.MAX_TG_MSG_LENGTH - pre_thread_msg_length,
        )

        messages = []
        for i, msg_part in enumerate(thread_list):
            if i == 0:
                last_part = (
                    message_part_two if len(thread_list) == 1 else msg.CONT_NEXT_MSG
                )
                messages.append(
                    f"{self.add_msg_text}"
                    f"{message_part_one.format(route=str(self.route))}\n\n{msg_part}"
                    f"\n\n{last_part}"
                )
            elif 1 <= i < len(thread_list) - 1:
                messages.append(f"{msg.CONTINUATION_MSG}\n\n{msg_part}")
            else:
                messages.append(
                    f"{msg.CONTINUATION_MSG}\n\n{msg_part}\n\n{message_part_two}"
                )
        logger.debug(f"Tthere are {len(messages)} messages to be sent.")
        return tuple(messages)

    @log(logger)
    def unlimit(self) -> Self:
        """Removes the closest departure limit from the timetable object."""
        self.limit = None
        return self

    def __repr__(self) -> str:
        """Returns the string representation of the Timetable object."""
        limit = f", limit={self.limit}" if self.limit else ""
        add_msg_text = (
            f", add_msg_text='{self.add_msg_text}'" if self.add_msg_text else ""
        )
        return (
            f"<{self.__class__.__name__} (date={self.date.strftime('%d.%m.%Y')}, "
            f"route={self.route}{limit}{add_msg_text})>"
        )
