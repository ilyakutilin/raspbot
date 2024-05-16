import abc
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from raspbot.core.exceptions import AlreadyExistsError
from raspbot.core.logging import configure_logging, log
from raspbot.db.base import async_session_factory

logger = configure_logging(__name__)

DatabaseModel = TypeVar("DatabaseModel")


class CRUDBase(abc.ABC):
    """Abstract base class for CRUD operations."""

    def __init__(
        self,
        model: DatabaseModel,
        session: AsyncSession = async_session_factory(),
    ):
        """Initializes CRUDBase class instance."""
        self._model = model
        self._session = session

    @log(logger)
    async def get_or_none(self, _id: int) -> DatabaseModel | None:
        """Gets the model object from the DB by its ID. Returns None if nonexistent."""
        async with self._session as session:
            db_obj = await session.execute(
                select(self._model).where(self._model.id == _id)
            )
            return db_obj.scalars().first()

    @log(logger)
    async def create(self, instance: DatabaseModel) -> DatabaseModel:
        """Creates the new model object and saves to DB."""
        async with self._session as session:
            session.add(instance)
            try:
                await session.commit()
            except IntegrityError:
                raise AlreadyExistsError(f"Instance {instance} already exists.")

            await session.refresh(instance)
            return instance
