from pydantic import BaseModel

from raspbot.db.stations import models


class BaseModelPD(BaseModel):
    """Base pydantic model."""

    def __repr__(self):
        """String representation of a pydantic model."""
        cols = []
        for col in self.model_fields.keys():
            cols.append(f"{col}={getattr(self, col)}")

        return f"<{self.__class__.__name__} ({', '.join(cols)})>"


class CodePD(BaseModelPD):
    """Code pydantic model."""

    yandex_code: str | None = None
    esr_code: str | None = None


class EntityPD(BaseModelPD):
    """Entity pydantic model."""

    codes: CodePD
    title: str

    def __str__(self):
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


class PointsByRegionPD(BaseModelPD):
    """Pydantic model for relationships between regions and points."""

    region_orm: models.RegionORM
    settlements: list[SettlementPD]
    stations: list[StationPD]

    class Config:
        """Config for the EntitiesByEntityPD pydantic model."""

        arbitrary_types_allowed = True

    def __repr__(self) -> str:
        """String representation of the PointsByRegion relationship."""
        return f"{self.__class__.__name__} {self.region_orm.title}"
