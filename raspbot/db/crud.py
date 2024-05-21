import abc
from typing import Type, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.base import BaseORM, async_session_factory

logger = configure_logging(__name__)

DatabaseModel = TypeVar("DatabaseModel", bound=BaseORM)


class CRUDBase(abc.ABC):
    """Abstract base class for CRUD operations."""

    def __init__(
        self,
        model: Type[DatabaseModel],
        session: AsyncSession = async_session_factory(),
    ):
        """Initializes CRUDBase class instance."""
        self._model = model
        self._session = session

    async def get_or_raise(self, _id: int) -> DatabaseModel:
        """Gets the model object from the DB by its ID. Returns None if nonexistent."""
        async with self._session as session:
            query = await session.execute(
                select(self._model).where(self._model.id == _id)
            )
            db_obj = query.scalars().first()
            if not db_obj:
                raise exc.NoDBObjectError(f"Object with id {_id} does not exist.")
            return db_obj

    async def create(self, instance: DatabaseModel) -> DatabaseModel:
        """Creates the new model object and saves to DB."""
        async with self._session as session:
            session.add(instance)
            try:
                await session.commit()
            except IntegrityError:
                raise exc.AlreadyExistsError(f"Instance {instance} already exists.")

            await session.refresh(instance)
            return instance
