import datetime as dt
import time
from typing import Self, TypedDict

from async_property import async_cached_property, async_property  # type: ignore
from pydantic import ValidationError

from raspbot.apicalls.search import TransportTypes, search_between_stations
from raspbot.bot.constants import messages as msg
from raspbot.core import exceptions as exc
from raspbot.core.email import send_email
from raspbot.core.logging import configure_logging, log
from raspbot.db.models import PointTypeEnum, RouteORM
from raspbot.db.routes.schema import RouteResponsePD, ThreadResponsePD
from raspbot.services.copyright import get_formatted_copyright
from raspbot.services.prettify_datetimes import prettify_day
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
        Returns raw JSON (as a dictionary) with the schedule from API.

        Accepts:
            - departure_code (str): Yandex code of the departure point as a string,
              example: “s2000006”
            - destination_code (str): Yandex code of the destination point as a string,
              example: “s9600721”

        Returns:
            dict: Full dictionary with all departures from Yandex (still raw data).

        Notes:
            The default pagination limit set by Yandex is 100 departures.
            In this function, when forming a query in kwargs_dict, this limit is
            not increased; instead, several dictionaries are formed, in which
            the pagination offset is gradually increased, and the departures
            of each new dictionary are added to the departures of the main dictionary.
        """

        class KwargsDict(TypedDict):
            from_: str
            to: str
            date: dt.date
            transport_types: str
            offset: int

        kwargs_dict: KwargsDict = {
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
        Turns the time string that came in the raw response into a datetime object.

        Accepts:
            raw_time (str): A time string from raw data.
            Acceptable formats:
                - ISO (example: 2023-05-29T12:48:00.00.000000)
                - HH:MM:SS (example: 12:48:00)

        Raises:
            InvalidTimeFormatError: called if the time format in the raw data string
            does not match the expected format and thus cannot be converted
            to a datetime object.

        Returns:
            A datetime object.
        """
        try:
            return dt.datetime.fromisoformat(raw_time)
        except ValueError as e:
            logger.error(
                f"Time from API is not in ISO format: {raw_time}. ValueError: {e}"
            )
            try:
                datetime_str = f"{self.date} {raw_time}"
                return dt.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                raise exc.InvalidTimeFormatError(
                    "Time from API is in an incorrect format. "
                    "2023-05-29T12:48:00.000000 or 12:48:00 are supported. Got "
                    f"{raw_time}. ValueError: {e}"
                )

    @log(logger)
    def _get_threadresponse_object(
        self,
        segment: dict,
        departure_time: dt.datetime | None = None,
    ) -> ThreadResponsePD:
        """Turns raw dict with thread into a ThreadResponse object."""
        try:
            if not departure_time:
                departure: dt.datetime = self._validate_time(
                    raw_time=segment["departure"]
                )
            arrival: dt.datetime = self._validate_time(raw_time=segment["arrival"])
        except exc.InvalidTimeFormatError as e:
            logger.exception(e)
            send_email(e)
            raise e
        except KeyError as e:
            logger.exception(e)
            send_email(e)
            raise exc.NoKeyError(e)

        try:
            short_title = segment["thread"]["short_title"]
            short_from_title = segment["from"]["short_title"]
            short_to_title = segment["to"]["short_title"]
            thread = segment["thread"]
            ticket_places = segment["tickets_info"]["places"]
            if not ticket_places:
                ticket_price = None
            else:
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
        except KeyError as e:
            logger.exception(e)
            send_email(e)
            raise exc.NoKeyError
        except ValidationError as e:
            logger.exception(e)
            send_email(e)
            raise e

    @log(logger)
    def format_thread_list(
        self,
        thread_list: list[ThreadResponsePD],
        max_length: int = settings.MAX_TG_MSG_LENGTH,
        max_threads_for_long_fmt: int = settings.MAX_THREADS_FOR_LONG_FMT,
    ) -> tuple[str, ...]:
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
        """Gets the full timetable in the form of a list of ThreadResponse objects."""
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
            except exc.InvalidTimeFormatError as e:
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
    async def _get_message_part_two(self, length: int) -> str:
        """Returns the second part of the message."""
        copyright_ = await get_formatted_copyright()
        if self.date != dt.date.today():
            return f"{msg.TYPE_DEPARTURE}\n\n{copyright_}"
        if self.limit or length <= settings.CLOSEST_DEP_LIMIT:
            return f"{msg.PRESS_DEPARTURE_BUTTON}\n\n{copyright_}"
        return f"{msg.PRESS_DEPARTURE_BUTTON_OR_TYPE}\n\n{copyright_}"

    @async_property
    async def msg(self) -> tuple[str, ...]:
        """
        Generates a tuple of messages prepared for Telegram.

        Returns a tuple consisting of messages with formatted departures ready to send.
        It is the tuple that is returned, since Telegram does not allow sending messages
        longer than a certain limit. Therefore, a tuple is an overall formatted message
        divided into parts, taking this limit into account.
        """
        logger.debug("Generating a tuple of messages to be replied to the user.")
        route = str(self.route)
        timetable = await self.timetable
        if not self.timetable:
            return (msg.NO_TODAY_DEPARTURES.format(route=route),)
        length = await self.length
        message_part_one = self._get_message_part_one(length=length, route=route)
        message_part_two = await self._get_message_part_two(length=length)
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


class ThreadInfo:
    """Information about a particular timetable thread."""

    def __init__(self, thread: ThreadResponsePD):
        """Initialize the ThreadInfo class instance."""
        self.thread = thread
        self.copyright = None

    @log(logger)
    def _format_price(self, price: float | None = None) -> str:
        if not price:
            if not self.thread.ticket_price:
                raise exc.NoPriceInThreadError(
                    f"There is no price in thread {self.thread.title}"
                )
            price = self.thread.ticket_price
        if price.is_integer():
            return f"{int(price)} ₽"
        return f"{price:.2f} ₽"

    @async_property
    async def msg(self):
        """Returns messag with information about the thread."""
        express = ", " + self.thread.express_type if self.thread.express_type else ""
        dep_platform = (
            ", " + self.thread.departure_platform
            if self.thread.departure_platform
            else ""
        )
        dep_terminal = (
            ", " + self.thread.departure_terminal
            if self.thread.departure_terminal
            else ""
        )
        dest_platform = (
            ", " + self.thread.arrival_platform if self.thread.arrival_platform else ""
        )
        dest_terminal = (
            ", " + self.thread.arrival_terminal if self.thread.arrival_terminal else ""
        )
        duration = time.strftime(
            f"{'%H ч. ' if self.thread.duration > 3600 else ''}%M мин.",
            time.gmtime(self.thread.duration),
        ).lstrip("0")
        ticket_price = (
            f"<b>Стоимость билета:</b> {self._format_price()}\n"
            if self.thread.ticket_price
            else ""
        )
        copyright_text = await get_formatted_copyright()
        logger.info(
            "Timetable thread info has been generated within "
            f"{self.__class__.__name__} class of {self.__class__.__module__} module."
        )
        return (
            f"<b>№ поезда:</b> {self.thread.number}\n"
            f"<b>Тип поезда:</b> {self.thread.transport_subtype}{express}\n"
            f"<b>Маршрут поезда:</b> {self.thread.title}\n"
            f"<b>Перевозчик:</b> {self.thread.carrier}\n"
            f"<b>Отправление от ст. {self.thread.from_}:</b> "
            f"{self.thread.str_time}{dep_platform}{dep_terminal}\n"
            f"<b>Прибытие на ст. {self.thread.to}:</b> "
            f"{self.thread.arrival.strftime(settings.DEP_FORMAT)}"
            f"{dest_platform}{dest_terminal}\n"
            f"<b>Останавливается:</b> {self.thread.stops}\n"
            f"<b>Время в пути:</b> {duration}\n"
            f"{ticket_price}\n{copyright_text}"
        )
