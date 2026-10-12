"""Composite indexes for bounded per-user history and insight queries."""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_sleep_sessions_user_local_date", "sleep_sessions", ["user_id", "local_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_sleep_sessions_user_local_date", table_name="sleep_sessions")
