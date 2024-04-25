"""empty message

Revision ID: 1246259c7272
Revises: a8164161daf2
Create Date: 2024-04-25 16:14:18.894666

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1246259c7272"
down_revision = "a8164161daf2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands typed inmanually as Alembic did not recognize Int => BigInt shift ###
    op.alter_column("user", "telegram_id", type_=sa.BIGINT())
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands typed inmanually as Alembic did not recognize Int => BigInt shift ###
    op.alter_column("user", "telegram_id", type_=sa.INTEGER())
    # ### end Alembic commands ###
