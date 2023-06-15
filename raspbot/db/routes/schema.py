from pydantic import BaseModel

from raspbot.db.stations import models


class PointResponse(BaseModel):
    id: int
    point_type: models.PointTypeEnum
    title: str
    yandex_code: str
    region_title: str
