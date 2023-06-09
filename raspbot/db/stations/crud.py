from typing import Generator

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from raspbot.db.base import get_session
from raspbot.db.crud import CRUDBase
from raspbot.db.stations.models import Country, Settlement, Station


class CRUDStations(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(Station, sessionmaker)

    async def get_stations_by_title(
        self, title: str, strict_search: bool = False
    ) -> list[Station]:
        search_template = "{title}" if strict_search else "%{title}%"
        async with self._sessionmaker() as session:
            stations = await session.execute(
                select(Station)
                .options(selectinload(Station.region))
                .join(Country)
                .where(
                    and_(
                        func.unaccent(Station.title).ilike(
                            search_template.format(title=title)
                        )
                    ),
                    (Station.transport_type == "train"),
                    Country.title == "Россия",
                )
                .order_by(Station.title)
                .limit(30)
            )
            return stations.scalars().unique().all()

    async def get_station_by_id(self, id: int) -> Station:
        async with self._sessionmaker() as session:
            station = await session.execute(
                select(Station)
                .options(selectinload(Station.region))
                .where(Station.id == id)
            )
            return station.scalars().first()


class CRUDSettlements(CRUDBase):
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session):
        super().__init__(Settlement, sessionmaker)

    async def get_settlements_by_title(
        self, title: str, strict_search: bool
    ) -> list[Station]:
        search_template = "{title}" if strict_search else "%{title}%"
        async with self._sessionmaker() as session:
            settlements = await session.execute(
                select(Settlement)
                .options(selectinload(Settlement.region))
                .join(Country)
                .where(
                    and_(
                        func.unaccent(Settlement.title).ilike(
                            search_template.format(title=title)
                        )
                    ),
                    Country.title == "Россия",
                )
                .order_by(Settlement.title)
                .limit(30)
            )
            return settlements.scalars().unique().all()

    async def get_settlement_by_id(self, id: int) -> Station:
        async with self._sessionmaker() as session:
            settlement = await session.execute(
                select(Settlement)
                .options(selectinload(Settlement.region))
                .where(Settlement.id == id)
            )
            return settlement.scalars().first()
