from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from raspbot.db.base import Base
from raspbot.db.stations.models import Point
from raspbot.services.shorteners.short_route import shorten_route_description
from raspbot.settings import settings


class User(Base):
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True)
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
    favorites: Mapped[list["Favorite"]] = relationship(
        "Favorite", back_populates="user"
    )
    recents: Mapped[list["Recent"]] = relationship("Recent", back_populates="user")

    @hybrid_property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


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
            f"{self.departure_point.title} {settings.ROUTE_INLINE_DELIMITER} "
            f"{self.destination_point.title}"
        )

    @property
    def short(self) -> str:
        return shorten_route_description(
            route_descr=self.__str__, limit=settings.ROUTE_INLINE_LIMIT
        )


class FavoriteRecentMixin(object):
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    route_id: Mapped[int] = mapped_column(ForeignKey("route.id"))
    added_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Favorite(Base, FavoriteRecentMixin):
    user: Mapped["User"] = relationship("User", back_populates="favorites")
    route: Mapped["Route"] = relationship("Route", back_populates="favorites_list")

    __table_args__ = (UniqueConstraint("user_id", "route_id", name="uq_user_favorite"),)


class Recent(Base, FavoriteRecentMixin):
    user: Mapped["User"] = relationship("User", back_populates="recents")
    route: Mapped["Route"] = relationship("Route", back_populates="recents_list")
    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", "route_id", name="uq_user_recent"),)
