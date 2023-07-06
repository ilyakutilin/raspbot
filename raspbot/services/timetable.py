import datetime as dt
from abc import ABC

from asyncinit import asyncinit
from pydantic import ValidationError

from raspbot.apicalls.search import TransportTypes, search_between_stations
from raspbot.bot.constants import messages as msg
from raspbot.core.exceptions import InvalidTimeFormatError
from raspbot.core.logging import configure_logging
from raspbot.db.models import Route
from raspbot.db.routes.schema import RouteResponse, ThreadResponse
from raspbot.settings import settings

logger = configure_logging(name=__name__)


class Timetable(ABC):
    async def _get_timetable_dict(
        self,
        departure_code: str,
        destination_code: str,
        date: dt.date = dt.date.today(),
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
        self, raw_time: str, timetable_date: dt.date = dt.date.today()
    ) -> dt.datetime:
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

    def _get_threadresponse_object(
        self,
        segment: dict,
        date: dt.date | None = None,
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
            if not date:
                timetable_date = dt.datetime.strptime(
                    segment["start_date"], "%Y-%m-%d"
                ).date()
            if not departure_time:
                departure: dt.datetime = self._validate_time(
                    raw_time=segment["departure"], timetable_date=timetable_date
                )
            arrival: dt.datetime = self._validate_time(
                raw_time=segment["arrival"], timetable_date=timetable_date
            )
        except InvalidTimeFormatError:  # TODO: Complete Exception handling
            logger.error("Error")
        except KeyError:  # TODO: Complete Exception handling
            logger.error("Error")
        except ValueError:  # TODO: Complete Exception handling
            logger.error("Error")

        try:
            short_title = segment.get("thread").get("short_title")

            uid_ = segment["thread"]["uid"]
            title_ = short_title if short_title else segment["thread"]["title"]
            express_type_ = segment["thread"]["express_type"]
            departure_ = departure_time if departure_time else departure
            arrival_ = arrival
            date_ = date if date else timetable_date

            logger.debug("Информация об аргументах объекта ThreadResponse:")
            logger.debug(f"uid = {uid_}, тип: {type(uid_)}")
            logger.debug(f"title = {title_}, тип: {type(title_)}")
            logger.debug(f"express_type = {express_type_}, тип: {type(express_type_)}")
            logger.debug(f"departure = {departure_}, тип: {type(departure_)}")
            logger.debug(f"arrival = {arrival_}, тип: {type(arrival_)}")
            logger.debug(f"date = {date_}, тип: {type(date_)}")

            threadresponse = ThreadResponse(
                uid=segment["thread"]["uid"],
                title=short_title if short_title else segment["thread"]["title"],
                express_type=segment["thread"]["express_type"],
                departure=departure_time if departure_time else departure,
                arrival=arrival,
                date=date if date else timetable_date,
            )
        except KeyError:  # TODO: Complete Exception handling
            logger.error("Error")
        except ValidationError:  # TODO: Complete Exception handling
            logger.error("Error")

        return threadresponse


@asyncinit
class ClosestTimetable(Timetable):
    async def __init__(self, route: RouteResponse | Route):
        self.route = route
        self.threads: list[ThreadResponse] = await self._get_closest_departures()

    def _get_closest_departures_for_date(
        self, date: dt.date, timetable_dict: dict, limit: int
    ) -> list[ThreadResponse]:
        """
        Генерирует список ближайших отправлений на указанную дату.

        Принимает на вход:
            - date_ (datetime): Дата, на которую требуется формирование списка ближайших
            отправлений;
            - timetable_dict (dict): Полный словарь (JSON) с сырыми данными,
            скомбинированный с учетом пагинации.
            - limit (int): Лимит количества отправлений.

        Возвращает:
            list[ThreadResponse]: Список установленного количества отправлений
            в формате ThreadResponse.
        """
        closest_departures: list[dt.datetime] = []
        for segment in timetable_dict["segments"]:
            raw_departure_time: str = segment["departure"]
            try:
                departure_time: dt.datetime = self._validate_time(
                    raw_time=raw_departure_time, timetable_date=date
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
            if departure_time.date() > date:
                logger.debug(
                    f"Отбраковка отправления: Поезд {departure_str} отправляется на "
                    "следующий день, поэтому не включается в выборку на указанную дату."
                )
            if len(closest_departures) >= limit:
                break
            threadresponse = self._get_threadresponse_object(
                segment=segment,
                # date=date,
                # departure_time=departure_time,
            )
            closest_departures.append(threadresponse)
            logger.debug(f"В список ближайших отправлений добавлено {departure_time}.")
        logger.debug(
            f"Финальное кол-во рейсов в списке на дату {date}: "
            f"{len(closest_departures)}"
        )
        return closest_departures

    async def _get_closest_departures(
        self,
    ) -> tuple[list[ThreadResponse], list[ThreadResponse]]:
        """
        Генерирует список ближайших отправлений по указанному маршруту.

        Если ближайших рейсов на сегодня нет или осталось очень мало,
        то показывается также несколько рейсов на завтра.

        Принимает на вход:
            - route (RouteResponse): Маршрут в формате RouteResponse или Route.

        Возвращает:
            - Кортеж из двух элементов: список рейсов на сегодня и список рейсов
            на завтра. Рейсы в формате ThreadResponse.
        """
        timetable_dict_today: dict = await self._get_timetable_dict(
            departure_code=self.route.departure_point.yandex_code,
            destination_code=self.route.destination_point.yandex_code,
            date=dt.date.today(),
        )
        closest_departures_today: list[
            ThreadResponse
        ] = self._get_closest_departures_for_date(
            date=dt.date.today(),
            timetable_dict=timetable_dict_today,
            limit=settings.CLOSEST_DEP_LIMIT,
        )
        remainder = max(0, settings.CLOSEST_DEP_LIMIT - len(closest_departures_today))
        closest_departures_tomorrow: list[ThreadResponse] = []
        last_departure_today: dt.datetime = (
            closest_departures_today[-1].departure
            if closest_departures_today
            else dt.timedelta(0)
        )
        current_time = (
            dt.datetime.now(tz=last_departure_today.tzinfo)
            if closest_departures_today
            else dt.timedelta(0)
        )
        if len(closest_departures_today) < settings.SMALL_REMAINDER or (
            ((last_departure_today - current_time) < dt.timedelta(hours=2))
            and remainder
        ):
            tomorrow = dt.date.today() + dt.timedelta(days=1)
            timetable_dict_tomorrow: dict = await self._get_timetable_dict(
                departure_code=self.route.departure_point.yandex_code,
                destination_code=self.route.destination_point.yandex_code,
                date=tomorrow,
            )
            closest_departures_tomorrow += self._get_closest_departures_for_date(
                date=tomorrow,
                timetable_dict=timetable_dict_tomorrow,
                limit=max(remainder, settings.SMALL_REMAINDER),
            )

        return closest_departures_today, closest_departures_tomorrow

    def _format_timetable_for_message(
        self,
        today_timetable: list[ThreadResponse],
        tomorrow_timetable: list[ThreadResponse],
        format: str,
    ) -> str:
        """
        Форматирует отправления (рейсы) и формирует готовое сообщение для Telegram.

        Принимает на вход:
            - today_timetable: Расписание на сегодня, которое необходимо
            отформатировать, в виде списка с объектами ThreadResponse.
            - today_timetable: Расписание на завтра, которое необходимо
            отформатировать, в виде списка с объектами ThreadResponse.
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
                    ttbl=", ".join(
                        [dep.departure.strftime(format) for dep in today_timetable]
                    ),
                    pb=msg.PRESS_DEPARTURE_BUTTON,
                )
            ),
            (True, True): (
                "{cd}\n{td}: {tdttbl}\n{tm}: {tmttbl}\n\n{pb}".format(
                    cd=msg.CLOSEST_DEPARTURES,
                    td=msg.TODAY,
                    tdttbl=", ".join(
                        [dep.departure.strftime(format) for dep in today_timetable]
                    ),
                    tm=msg.TOMORROW,
                    tmttbl=", ".join(
                        [dep.departure.strftime(format) for dep in tomorrow_timetable]
                    ),
                    pb=msg.PRESS_DEPARTURE_BUTTON,
                )
            ),
            (False, True): (
                "{ot}\n{ttbl}\n\n{pb}".format(
                    ot=msg.ONLY_TOMORROW,
                    ttbl=", ".join(
                        [dep.departure.strftime(format) for dep in tomorrow_timetable]
                    ),
                    pb=msg.PRESS_DEPARTURE_BUTTON,
                )
            ),
            (False, False): msg.NO_CLOSEST_DEPARTURES,
        }
        return ttbl_dict[(bool(today_timetable), bool(tomorrow_timetable))]

    def _format_timetable_for_buttons(
        self,
        today_timetable: list[ThreadResponse],
        tomorrow_timetable: list[ThreadResponse],
        format: str,
    ) -> list[str]:
        """
        Форматирует отправления (рейсы) и формирует строки для инлайн-кнопок.

        Принимает на вход:
            - today_timetable: Расписание на сегодня, которое необходимо
            отформатировать, в виде списка с объектами ThreadResponse.
            - today_timetable: Расписание на завтра, которое необходимо
            отформатировать, в виде списка с объектами ThreadResponse.
            - format: Формат времени, к которому необходимо привести отправления.

        Примечания:
            ttbl_dict представляет собой словарь, ключом которого является кортеж из
            булевых значений списков расписаний на сегодня (первая позиция кортежа)
            и на завтра (вторая позиция) соответственно.
            Например, (True, False) следует читать как "в списке отправлений на сегодня
            есть рейсы, а список на завтра пустой. Значит, нужно сформировать кнопки,
            в которых будут только рейсы на сегодня".

        Возвращает:
            - Список строк, представляющих собой текст для инлайн-кнопки о рейсе.
        """
        ttbl_dict = {
            (True, False): [dep.strftime(format) for dep in today_timetable],
            (True, True): (
                [f"{msg.TODAY} {dep.strftime(format)}" for dep in today_timetable]
                + [
                    f"{msg.TOMORROW} {dep.strftime(format)}"
                    for dep in tomorrow_timetable
                ]
            ),
            (False, True): [
                f"{msg.TOMORROW} {dep.strftime(format)}" for dep in tomorrow_timetable
            ],
            (False, False): [],
        }
        return ttbl_dict[(bool(today_timetable), bool(tomorrow_timetable))]

    async def msg(self) -> str:
        """
        Генерирует список ближайших отправлений по указанному маршруту для сообщения.

        Если ближайших рейсов на сегодня нет или осталось очень мало,
        то показывается также несколько рейсов на завтра.

        Принимает на вход:
            - route (RouteResponse): Маршрут в формате RouteResponse или Route.

        Возвращает:
            - str: Отформатированный текст с ближайшими отправлениями, готовый к вставке
            в сообщение Telegram.
        """
        today, tomorrow = await self._get_closest_departures()
        formatted_timetable: str = self._format_timetable_for_message(
            today_timetable=today,
            tomorrow_timetable=tomorrow,
            format=settings.DEP_FORMAT,
        )
        return formatted_timetable

    async def btn(self) -> list[str]:
        """
        Генерирует список ближайших отправлений по указанному маршруту для кнопок.

        Если ближайших рейсов на сегодня нет или осталось очень мало,
        то выводится также несколько рейсов на завтра.

        Принимает на вход:
            - route (RouteResponse): Маршрут в формате RouteResponse или Route.

        Возвращает:
            - Список строк, представляющих собой текст для инлайн-кнопки о рейсе.
        """
        today, tomorrow = await self._get_closest_departures()
        formatted_timetable: list[str] = self._format_timetable_for_buttons(
            today_timetable=today,
            tomorrow_timetable=tomorrow,
            format=settings.DEP_FORMAT,
        )
        return formatted_timetable
