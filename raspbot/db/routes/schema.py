import datetime as dt

from pydantic import BaseModel

from raspbot.db.models import PointTypeEnum, RouteStrMixin
from raspbot.settings import settings


class PointResponse(BaseModel):
    """Pydantic model for route points."""

    id: int
    point_type: PointTypeEnum
    title: str
    yandex_code: str
    region_title: str


class RouteResponse(BaseModel, RouteStrMixin):
    """Pydantic model for routes."""

    id: int
    departure_point: PointResponse
    destination_point: PointResponse


class ThreadResponse(BaseModel):
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
    # TODO: Ticket prices
    ticket_price: float

    @property
    def str_time(self) -> str:
        """String representation of the departure time."""
        return self.departure.strftime(settings.DEP_FORMAT)

    @property
    def str_time_with_express_type(self) -> str:
        """String representation of the departure time with express type."""
        return f"<b>{self.str_time}{'э' if self.express_type else ''}</b>"

    @property
    def message_with_route(self) -> str:
        """String representation of the departure time with express and route."""
        return f"{self.str_time_with_express_type} ({self.title})"

    @property
    def message_with_departure_station(self) -> str:
        """String representation of the departure time with departure station."""
        return f"{self.str_time_with_express_type}, от ст. {self.from_}"

    @property
    def message_with_destination_station(self) -> str:
        """String representation of the departure time with destination station."""
        return f"{self.str_time_with_express_type}, до ст. {self.to}"

    @property
    def message_with_departure_and_destination(self) -> str:
        """String representation of the dep time with dep and dest stations."""
        return (
            f"{self.str_time_with_express_type}, от ст. {self.from_} до ст. {self.to}"
        )
