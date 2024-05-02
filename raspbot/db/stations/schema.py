from pydantic import BaseModel

from raspbot.db.stations import models


class Code(BaseModel):
    """Base pydantic model with fields used by all models."""

    yandex_code: str | None = None
    esr_code: str | None = None


class Entity(BaseModel):
    """Entity pydantic model."""

    codes: Code
    title: str

    def __repr__(self):
        """String representation of the Entity pydantic model."""
        return f"{self.__class__.__name__} {self.title}"


class Station(Entity):
    """Station pydantic model."""

    direction: str
    station_type: str
    longitude: float | str
    transport_type: str
    latitude: float | str


class Settlement(Entity):
    """Settlement pydantic model."""

    stations: list[Station]


class Region(Entity):
    """Region pydantic model."""

    settlements: list[Settlement]


class Country(Entity):
    """Country pydantic model."""

    regions: list[Region]


class World(BaseModel):
    """World pydantic model."""

    countries: list[Country]


class EntitiesByEntity(BaseModel):
    """Base pydantic model for relationships between entities."""

    class Config:
        """Config for the EntitiesByEntity pydantic model."""

        arbitrary_types_allowed = True


class RegionsByCountry(EntitiesByEntity):
    """Pydantic model for relationships between countries and regions."""

    country: models.CountryORM
    regions: list[Region]

    def __repr__(self) -> str:
        """String representation of the RegionsByCountry relationship."""
        return f"{self.__class__.__name__} {self.country.title}"


class PointsByRegion(EntitiesByEntity):
    """Pydantic model for relationships between regions and points."""

    region: models.RegionORM
    settlements: list[Settlement]
    stations: list[Station]

    def __repr__(self) -> str:
        """String representation of the PointsByRegion relationship."""
        return f"{self.__class__.__name__} {self.region.title}"
