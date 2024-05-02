from pydantic import BaseModel as BaseModelPD

from raspbot.db.stations import models


class CodePD(BaseModelPD):
    """Code pydantic model."""

    yandex_code: str | None = None
    esr_code: str | None = None


class EntityPD(BaseModelPD):
    """Entity pydantic model."""

    codes: CodePD
    title: str

    def __repr__(self):
        """String representation of the Entity pydantic model."""
        return f"{self.__class__.__name__} {self.title}"


class StationPD(EntityPD):
    """Station pydantic model."""

    direction: str
    station_type: str
    longitude: float | str
    transport_type: str
    latitude: float | str


class SettlementPD(EntityPD):
    """Settlement pydantic model."""

    stations: list[StationPD]


class RegionPD(EntityPD):
    """Region pydantic model."""

    settlements: list[SettlementPD]


class CountryPD(EntityPD):
    """Country pydantic model."""

    regions: list[RegionPD]


class WorldPD(BaseModelPD):
    """World pydantic model."""

    countries: list[CountryPD]


class EntitiesByEntityPD(BaseModelPD):
    """Base pydantic model for relationships between entities."""

    class Config:
        """Config for the EntitiesByEntityPD pydantic model."""

        arbitrary_types_allowed = True


class RegionsByCountryPD(EntitiesByEntityPD):
    """Pydantic model for relationships between countries and regions."""

    country: models.CountryORM
    regions: list[RegionPD]

    def __repr__(self) -> str:
        """String representation of the RegionsByCountry relationship."""
        return f"{self.__class__.__name__} {self.country.title}"


class PointsByRegionPD(EntitiesByEntityPD):
    """Pydantic model for relationships between regions and points."""

    region: models.RegionORM
    settlements: list[SettlementPD]
    stations: list[StationPD]

    def __repr__(self) -> str:
        """String representation of the PointsByRegion relationship."""
        return f"{self.__class__.__name__} {self.region.title}"
