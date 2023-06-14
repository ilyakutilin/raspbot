from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from raspbot.db.base import Base
from raspbot.db.stations.models import Point


class User(Base):
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    telegram_id: Mapped[int] = mapped_column(Integer)
    language_code: Mapped[str] = mapped_column(String(100))
    added_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class Route(Base):
    departure_point_id: Mapped[int] = mapped_column(ForeignKey("point.id"))
    departure_point: Mapped["Point"] = relationship("Point", back_populates="routes")
    destination_point_id: Mapped[int] = mapped_column(ForeignKey("point.id"))
    destination_point: Mapped["Point"] = relationship("Point", back_populates="routes")
