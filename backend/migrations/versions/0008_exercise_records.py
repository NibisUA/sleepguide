"""User-owned exercise definitions and results; records/streaks are derived."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_workouts_id_user_id", "workouts", ["id", "user_id"])
    op.create_table(
        "exercises",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("name_key", sa.String(240), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "name_key", name="uq_exercises_user_name_key"),
        sa.UniqueConstraint("id", "user_id", name="uq_exercises_id_user_id"),
        sa.CheckConstraint("kind IN ('strength', 'cardio')", name="kind"),
    )
    op.create_table(
        "exercise_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workout_id", sa.BigInteger(), nullable=False),
        sa.Column("exercise_id", sa.BigInteger(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(7, 2)),
        sa.Column("reps", sa.Integer()),
        sa.Column("distance_m", sa.Integer()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["workout_id", "user_id"], ["workouts.id", "workouts.user_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id", "user_id"], ["exercises.id", "exercises.user_id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "(weight_kg IS NOT NULL AND weight_kg BETWEEN 0 AND 2000 AND reps BETWEEN 1 AND 1000 "
            "AND reps IS NOT NULL AND distance_m IS NULL AND duration_seconds IS NULL) OR "
            "(weight_kg IS NULL AND reps IS NULL AND distance_m BETWEEN 1 AND 1000000 "
            "AND distance_m IS NOT NULL AND (duration_seconds IS NULL OR "
            "duration_seconds BETWEEN 1 AND 21600))",
            name="metrics",
        ),
    )
    op.create_index("ix_exercise_logs_user_exercise", "exercise_logs", ["user_id", "exercise_id"])
    op.create_index("ix_exercise_logs_user_workout", "exercise_logs", ["user_id", "workout_id"])


def downgrade():
    op.drop_table("exercise_logs")
    op.drop_table("exercises")
    op.drop_constraint("uq_workouts_id_user_id", "workouts", type_="unique")
