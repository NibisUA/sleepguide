"""User-controlled reminder notification sound.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("reminder_sound_on", sa.Boolean(), nullable=False, server_default="true")
    )


def downgrade():
    op.drop_column("users", "reminder_sound_on")
