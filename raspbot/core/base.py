"""Imports of class Base and all models for Alembic."""
from raspbot.db.base import Base  # noqa
from raspbot.db.routes.models import Route  # noqa
from raspbot.db.stations.models import Country, Point, Region  # noqa
from raspbot.db.users.models import Favorite, Recent, User  # noqa
