from typing import Generator

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.stations.models import Country, Region, Settlement, Station


class CRUDStations(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(Station, sessionmaker)

    async def get_stations_by_title(self, title: str) -> list[Station]:
        async with self._sessionmaker() as session:
            stations = await session.execute(
                select(Station)
                .options(selectinload(Station.region))
                .join(Country)
                .where(
                    and_(Station.title.ilike(f"{title}%")),
                    (Station.transport_type == "train"),
                    Country.title == "Россия",
                )
            )
            return stations.scalars().unique().all()


class CRUDSettlements(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(Settlement, sessionmaker)

    async def get_settlements_by_title(self, title: str) -> list[Station]:
        async with self._sessionmaker() as session:
            settlements = await session.execute(
                select(Settlement)
                .options(selectinload(Settlement.region))
                .join(Country)
                .where(
                    and_(Settlement.title.ilike(f"{title}%")),
                    Country.title == "Россия",
                )
            )
            return settlements.scalars().unique().all()
