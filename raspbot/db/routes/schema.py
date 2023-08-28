import datetime as dt

from pydantic import BaseModel

from raspbot.db.models import PointTypeEnum
from raspbot.services.shorteners import get_short_point_type, shorten_route_description
from raspbot.settings import settings


class PointResponse(BaseModel):
    id: int
    point_type: PointTypeEnum
    title: str
    yandex_code: str
    region_title: str


class RouteResponse(BaseModel):
    id: int
    departure_point: PointResponse
    destination_point: PointResponse

    def __str__(self) -> str:
        return (
            f"{get_short_point_type(self.departure_point.point_type)} "
            f"{self.departure_point.title}{settings.ROUTE_INLINE_DELIMITER}"
            f"{get_short_point_type(self.destination_point.point_type)} "
            f"{self.destination_point.title}"
        )

    @property
    def short(self) -> str:
        return shorten_route_description(
            route_descr=self.__str__(), limit=settings.ROUTE_INLINE_LIMIT
        )


class ThreadResponse(BaseModel):
    uid: str
    number: str
    title: str
    carrier: str
    transport_subtype: str | None
    express_type: str | None
    from_: str
    to: str
    departure: dt.datetime
    arrival: dt.datetime
    date: dt.date
    stops: str
    departure_platform: str | None
    arrival_platform: str | None
    departure_terminal: str | None
    arrival_terminal: str | None
    duration: float
    # TODO: Ticket prices
    ticket_price: float

    @property
    def str_time(self) -> str:
        return self.departure.strftime(settings.DEP_FORMAT)

    @property
    def str_time_with_express_type(self) -> str:
        return f"<b>{self.str_time}{'э' if self.express_type else ''}</b>"

    @property
    def message_with_route(self) -> str:
        return f"{self.str_time_with_express_type} ({self.title})"

    @property
    def message_with_departure_station(self) -> str:
        return f"{self.str_time_with_express_type}, от ст. {self.from_}"

    @property
    def message_with_destination_station(self) -> str:
        return f"{self.str_time_with_express_type}, до ст. {self.to}"

    @property
    def message_with_departure_and_destination(self) -> str:
        return (
            f"{self.str_time_with_express_type}, от ст. {self.from_} до ст. {self.to}"
        )
