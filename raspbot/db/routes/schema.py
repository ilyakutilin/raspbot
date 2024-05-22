import datetime as dt
from typing import Protocol

from pydantic import BaseModel as BaseModelPD

from raspbot.db.stations.models import PointORM, PointTypeEnum
from raspbot.services.shorteners import get_short_point_type, shorten_route_description
from raspbot.settings import settings


class PointResponsePD(BaseModelPD):
    """Pydantic model for route points."""

    id: int
    point_type: PointTypeEnum
    title: str
    yandex_code: str
    region_title: str


class RouteProtocol(Protocol):
    """Protocol for routes."""

    departure_point: PointORM | PointResponsePD
    destination_point: PointORM | PointResponsePD


class RouteStrMixin:
    """Mixin for Route string representation."""

    def __str__(self: "RouteProtocol") -> str:
        """String representation."""
        return (
            f"{get_short_point_type(self.departure_point.point_type)} "
            f"{self.departure_point.title}{settings.ROUTE_INLINE_DELIMITER}"
            f"{get_short_point_type(self.destination_point.point_type)} "
            f"{self.destination_point.title}"
        )

    @property
    def short(self: "RouteProtocol") -> str:
        """Shortened route string representation."""
        return shorten_route_description(
            route_descr=self.__str__(), limit=settings.ROUTE_INLINE_LIMIT
        )


class RouteResponsePD(RouteStrMixin, BaseModelPD):
    """Pydantic model for routes."""

    id: int
    departure_point: PointResponsePD
    destination_point: PointResponsePD


class ThreadResponsePD(BaseModelPD):
    """Pydantic model for the timetable thread."""

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
    ticket_price: float

    @property
    def str_time(self) -> str:
        """String representation of the departure time."""
        return self.departure.strftime(settings.DEP_FORMAT)

    @property
    def str_time_with_express_type(self) -> str:
        """String representation of the departure time with express type."""
        return f"{self.str_time}{'э' if self.express_type else ''}"

    @property
    def bold_str_time_with_express_type(self) -> str:
        """String representation of the departure time with express type."""
        return f"<b>{self.str_time}{'э' if self.express_type else ''}</b>"

    @property
    def message_with_route(self) -> str:
        """String representation of the departure time with express and route."""
        return f"{self.bold_str_time_with_express_type} ({self.title})"

    @property
    def message_with_departure_station(self) -> str:
        """String representation of the departure time with departure station."""
        return f"{self.bold_str_time_with_express_type}, от ст. {self.from_}"

    @property
    def message_with_destination_station(self) -> str:
        """String representation of the departure time with destination station."""
        return f"{self.bold_str_time_with_express_type}, до ст. {self.to}"

    @property
    def message_with_departure_and_destination(self) -> str:
        """String representation of the dep time with dep and dest stations."""
        return (
            f"{self.bold_str_time_with_express_type}, от ст. {self.from_} "
            f"до ст. {self.to}"
        )
