"""stress_logs

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stress_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name=op.f("ck_stress_logs_level_range")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_stress_logs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stress_logs")),
    )
    op.create_index(op.f("ix_stress_logs_user_id"), "stress_logs", ["user_id"])
    op.create_index("ix_stress_logs_user_local_date", "stress_logs", ["user_id", "local_date"])


def downgrade() -> None:
    op.drop_index("ix_stress_logs_user_local_date", table_name="stress_logs")
    op.drop_index(op.f("ix_stress_logs_user_id"), table_name="stress_logs")
    op.drop_table("stress_logs")
