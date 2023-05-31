from pydantic import BaseModel

from raspbot.db.stations import models


class Code(BaseModel):
    yandex_code: str | None = None
    esr_code: str | None = None


class Entity(BaseModel):
    codes: Code
    title: str

    def __repr__(self):
        return f"{self.__class__.__name__} {self.title}"


class Station(Entity):
    direction: str
    station_type: str
    longitude: float | str
    transport_type: str
    latitude: float | str


class Settlement(Entity):
    stations: list[Station]


class Region(Entity):
    settlements: list[Settlement]


class Country(Entity):
    regions: list[Region]


class World(BaseModel):
    countries: list[Country]


class EntitiesByEntity(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class RegionsByCountry(EntitiesByEntity):
    country: models.Country
    regions: list[Region]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} {self.country.title}"


class SettlementsByRegion(EntitiesByEntity):
    region: models.Region
    settlements: list[Settlement]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} {self.region.title}"


class StationsBySettlement(EntitiesByEntity):
    settlement: models.Settlement
    stations: list[Station]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} {self.settlement.title}"


class PointResponse(BaseModel):
    is_station: bool
    title: str
    yandex_code: str
    region_title: str
