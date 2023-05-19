from pydantic import BaseModel


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
