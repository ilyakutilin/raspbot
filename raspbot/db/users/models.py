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

from raspbot.db.base import BaseORM
from raspbot.db.stations.models import PointORM
from raspbot.services.shorteners import get_short_point_type, shorten_route_description
from raspbot.settings import settings


class UserORM(BaseORM):
    """User model."""

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    first_name: Mapped[str] = mapped_column(String(100), default="")
    last_name: Mapped[str | None] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(100))
    language_code: Mapped[str | None] = mapped_column(String(100))
    recents: Mapped[list["RecentORM"]] = relationship(
        "RecentORM", back_populates="user"
    )

    @hybrid_property
    def full_name(self) -> str:
        """Full name of the user."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


class RouteStrMixin:
    """Mixin for Route string representation."""

    def __str__(self) -> str:
        """String representation."""
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


class RouteORM(BaseORM, RouteStrMixin):
    """Route model."""

    departure_point_id: Mapped[int] = mapped_column(ForeignKey("points.id"))
    departure_point: Mapped["PointORM"] = relationship(
        "PointORM", foreign_keys=[departure_point_id]
    )
    destination_point_id: Mapped[int] = mapped_column(ForeignKey("points.id"))
    destination_point: Mapped["PointORM"] = relationship(
        "PointORM", foreign_keys=[destination_point_id]
    )
    recents_list: Mapped[list["RecentORM"]] = relationship(
        "RecentORM", back_populates="route"
    )

    __table_args__ = (
        UniqueConstraint(
            "departure_point_id",
            "destination_point_id",
            name="uq_departure_destination",
        ),
    )


class RecentORM(BaseORM):
    """Model for recent and favorite routes.

    Recent and favorite is the same model.
    Favorite is implemented by a 'favorite' boolean field.
    A route needs to be in the recents to be added to favorites.
    """

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"))
    count: Mapped[int] = mapped_column(Integer(), default=0)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped["UserORM"] = relationship("UserORM", back_populates="recents")
    route: Mapped["RouteORM"] = relationship("RouteORM", back_populates="recents_list")

    __table_args__ = (UniqueConstraint("user_id", "route_id", name="uq_user_recent"),)
