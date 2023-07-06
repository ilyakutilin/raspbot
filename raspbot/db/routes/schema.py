import datetime as dt

from pydantic import BaseModel

from raspbot.db.models import PointTypeEnum


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


class ThreadResponse(BaseModel):
    uid: str
    title: str
    express_type: str | None
    departure: dt.datetime
    arrival: dt.datetime
    date: dt.date
