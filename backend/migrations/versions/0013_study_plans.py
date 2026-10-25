"""Deadline preparation plans and immutable progress events."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "study_plans",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("reserve_days", sa.Integer(), nullable=False),
        sa.Column("daily_capacity", sa.Integer(), nullable=True),
        sa.Column("items", JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("id", "user_id", name="uq_study_plans_id_user_id"),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])
    op.create_table(
        "study_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("detail", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "user_id"], ["study_plans.id", "study_plans.user_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_study_events_user_id", "study_events", ["user_id"])


def downgrade():
    op.drop_table("study_events")
    op.drop_table("study_plans")
