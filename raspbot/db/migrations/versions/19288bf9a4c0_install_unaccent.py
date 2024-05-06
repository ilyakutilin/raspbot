"""Install unaccent

Revision ID: 19288bf9a4c0
Revises: fffba5d27d29
Create Date: 2024-05-06 10:01:11.576819

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "19288bf9a4c0"
down_revision = "fffba5d27d29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS unaccent;")
