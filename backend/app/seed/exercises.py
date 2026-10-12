"""Synthetic exercise results for the dev-login account; never runs in production."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Exercise, ExerciseLog, Workout


async def seed_exercises(session: AsyncSession, user_id: int, workouts: list[Workout]) -> None:
    if get_settings().env != "dev":
        raise RuntimeError("Exercise demo data is allowed only with ENV=dev")
    strength = Exercise(user_id=user_id, name="Жим лежачи", name_key="жим лежачи", kind="strength")
    cardio = Exercise(user_id=user_id, name="Біг", name_key="біг", kind="cardio")
    session.add_all([strength, cardio])
    await session.flush()
    for index, workout in enumerate(workouts[-6:]):
        if index % 2 == 0:
            workout.type = "gym"
            session.add(
                ExerciseLog(
                    user_id=user_id,
                    workout_id=workout.id,
                    exercise_id=strength.id,
                    weight_kg=50 + index * 2.5,
                    reps=8 + index,
                )
            )
        else:
            workout.type = "running"
            session.add(
                ExerciseLog(
                    user_id=user_id,
                    workout_id=workout.id,
                    exercise_id=cardio.id,
                    distance_m=5000,
                    duration_seconds=1700 - index * 40,
                )
            )
