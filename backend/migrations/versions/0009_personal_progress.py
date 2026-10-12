"""Personal reminder preferences, weekly targets and voluntary sleep feedback."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("reminder_pattern_on", sa.Boolean(), server_default="false", nullable=False),
    )
    for kind, default in (("sleep", "5"), ("workout", "3"), ("stress", "3"), ("screen", "3")):
        op.add_column(
            "users",
            sa.Column(f"weekly_{kind}_days", sa.Integer(), server_default=default, nullable=False),
        )
    op.create_table(
        "sleep_feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("limited_data", sa.Boolean(), nullable=False),
        sa.Column("algorithm_version", sa.String(16), nullable=False),
        sa.Column("context_signature", sa.String(64), nullable=False),
        sa.Column("components", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "local_date", name="uq_sleep_feedback_user_date"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="rating"),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="score"),
    )


def downgrade():
    op.drop_table("sleep_feedback")
    for kind in ("sleep", "workout", "stress", "screen"):
        op.drop_column("users", f"weekly_{kind}_days")
    op.drop_column("users", "reminder_pattern_on")
