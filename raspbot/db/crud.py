import abc
import contextlib
from typing import Generator, TypeVar

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from raspbot.core.exceptions import AlreadyExistsError, NotFoundError
from raspbot.db.base import get_session

DatabaseModel = TypeVar("DatabaseModel")


class CRUDBase(abc.ABC):
    """Abstract base class for CRUD operations."""

    def __init__(
        self,
        model: DatabaseModel,
        sessionmaker: Generator[AsyncSession, None, None] = get_session,
    ):
        """Initializes CRUDBase class instance."""
        self._model = model
        self._sessionmaker = contextlib.asynccontextmanager(sessionmaker)

    async def get_or_none(self, _id: int) -> DatabaseModel | None:
        """Gets the model object from the DB by its ID. Returns None if nonexistent."""
        async with self._sessionmaker() as session:
            db_obj = await session.execute(
                select(self._model).where(self._model.id == _id)
            )
            return db_obj.scalars().first()

    async def get(self, _id: int) -> DatabaseModel:
        """Gets the model object by its ID. Throws exception if nonexistent."""
        db_obj = await self.get_or_none(_id)
        if db_obj is None:
            raise NotFoundError(
                f"Object {self._model.__name__} with id {_id} is not found."
            )
        return db_obj

    async def get_all(self) -> list[DatabaseModel]:
        """Returns all the model objects from DB."""
        async with self._sessionmaker() as session:
            db_objs = await session.execute(select(self._model))
            return db_objs.scalars().all()

    async def create(self, instance: DatabaseModel) -> DatabaseModel:
        """Creates the new model object and saves to DB."""
        async with self._sessionmaker() as session:
            session.add(instance)
            try:
                await session.commit()
            except IntegrityError:
                raise AlreadyExistsError(f"Instance {instance} already exists.")

            await session.refresh(instance)
            return instance

    async def create_multi(self, objects: list[DatabaseModel]) -> None:
        """Creates several model objects in DB."""
        async with self._sessionmaker() as session:
            session.add_all(objects)
            session.commit()

    async def update(self, _id: int, instance: DatabaseModel) -> DatabaseModel:
        """Updates the existing model object in DB."""
        async with self._sessionmaker() as session:
            instance.id = _id
            instance = await session.merge(instance)
            await session.commit()
            return instance

    async def update_multi(self, instances: list[dict]) -> list[DatabaseModel]:
        """Updates several modified model objects in DB."""
        async with self._sessionmaker() as session:
            await session.execute(update(self._model), instances)
            session.commit()
            return instances
