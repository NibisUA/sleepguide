"""reminder idempotency markers on users

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_evening_reminder_date", sa.Date(), nullable=True))
    op.add_column(
        "users", sa.Column("last_morning_reminder_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "last_morning_reminder_at")
    op.drop_column("users", "last_evening_reminder_date")
