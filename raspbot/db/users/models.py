from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from raspbot.db.base import Base
from raspbot.db.stations.models import Point
from raspbot.services.shorteners import get_short_point_type, shorten_route_description
from raspbot.settings import settings


class User(Base):
    """User model."""

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    first_name: Mapped[str] = mapped_column(String(100), default="")
    last_name: Mapped[str | None] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(100))
    language_code: Mapped[str | None] = mapped_column(String(100))
    added_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    recents: Mapped[list["Recent"]] = relationship("Recent", back_populates="user")

    @hybrid_property
    def full_name(self) -> str:
        """Full name of the user."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


class Route(Base):
    """Route model."""

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
        """String representation of the route."""
        return (
            f"{get_short_point_type(self.departure_point.point_type)} "
            f"{self.departure_point.title}{settings.ROUTE_INLINE_DELIMITER}"
            f"{get_short_point_type(self.destination_point.point_type)} "
            f"{self.destination_point.title}"
        )

    @property
    def short(self) -> str:
        """Shortened route string representation."""
        return shorten_route_description(
            route_descr=self.__str__(), limit=settings.ROUTE_INLINE_LIMIT
        )


class Recent(Base):
    """Model for recent and favorite routes.

    Recent and favorite is the same model.
    Favorite is implemented by a 'favorite' boolean field.
    A route needs to be in the recents to be added to favorites.
    """

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    route_id: Mapped[int] = mapped_column(ForeignKey("route.id"))
    added_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    count: Mapped[int] = mapped_column(Integer(), default=0)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped["User"] = relationship("User", back_populates="recents")
    route: Mapped["Route"] = relationship("Route", back_populates="recents_list")

    __table_args__ = (UniqueConstraint("user_id", "route_id", name="uq_user_recent"),)
