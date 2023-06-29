from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from raspbot.db.base import Base
from raspbot.db.stations.models import Point
from raspbot.db.users.models import Favorite, Recent
from raspbot.services.shorteners import get_short_point_type, shorten_route_description
from raspbot.settings import settings


class Route(Base):
    departure_point_id: Mapped[int] = mapped_column(ForeignKey("point.id"))
    departure_point: Mapped["Point"] = relationship(
        "Point", foreign_keys=[departure_point_id]
    )
    destination_point_id: Mapped[int] = mapped_column(ForeignKey("point.id"))
    destination_point: Mapped["Point"] = relationship(
        "Point", foreign_keys=[destination_point_id]
    )
    added_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    favorites_list: Mapped[list["Favorite"]] = relationship(
        "Favorite", back_populates="route"
    )
    recents_list: Mapped[list["Recent"]] = relationship(
        "Recent", back_populates="route"
    )

    __table_args__ = (
        UniqueConstraint(
            "departure_point_id",
            "destination_point_id",
            name="uq_departure_destination",
        ),
    )

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
