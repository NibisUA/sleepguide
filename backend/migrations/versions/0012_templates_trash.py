"""Saved workout plans and recoverable diary deletion."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workouts", sa.Column("planned_sets", JSONB(), nullable=False, server_default="[]")
    )
    op.create_table(
        "workout_templates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("intensity", sa.String(16), nullable=False),
        sa.Column("sets", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_workout_templates_user_id", "workout_templates", ["user_id"])
    op.create_table(
        "deleted_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deleted_entries_user_id", "deleted_entries", ["user_id"])
    op.create_index("ix_deleted_entries_expires_at", "deleted_entries", ["expires_at"])


def downgrade():
    op.drop_table("deleted_entries")
    op.drop_table("workout_templates")
    op.drop_column("workouts", "planned_sets")
