from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Imports of models for Alembic
from raspbot.db.stations.models import Country, Region, Settlement, Station  # noqa
from raspbot.settings import settings


class PreBase:
    @declared_attr
    def __tablename__(cls):
        return f"{cls.__name__.lower()}s"

    id: Mapped[int] = mapped_column(primary_key=True)


class Base(AsyncAttrs, DeclarativeBase, PreBase):
    pass


engine = create_async_engine(settings.database_url)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
