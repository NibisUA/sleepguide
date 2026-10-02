"""users and sleep_sessions

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("sleep_goal_minutes", sa.Integer(), nullable=False),
        sa.Column("target_bedtime", sa.Time(), nullable=True),
        sa.Column("reminder_evening_time", sa.Time(), nullable=True),
        sa.Column("reminder_morning_on", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_telegram_user_id"), "users", ["telegram_user_id"], unique=True)

    op.create_table(
        "sleep_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("local_date", sa.Date(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("is_nap", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_sleep_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sleep_sessions")),
    )
    op.create_index(op.f("ix_sleep_sessions_user_id"), "sleep_sessions", ["user_id"])
    op.create_index(op.f("ix_sleep_sessions_local_date"), "sleep_sessions", ["local_date"])
    op.create_index(
        "ux_sleep_one_open_per_user",
        "sleep_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_sleep_one_open_per_user", table_name="sleep_sessions")
    op.drop_index(op.f("ix_sleep_sessions_local_date"), table_name="sleep_sessions")
    op.drop_index(op.f("ix_sleep_sessions_user_id"), table_name="sleep_sessions")
    op.drop_table("sleep_sessions")
    op.drop_index(op.f("ix_users_telegram_user_id"), table_name="users")
    op.drop_table("users")
