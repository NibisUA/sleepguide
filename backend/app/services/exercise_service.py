from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, ExerciseLog, User, Workout
from app.schemas.exercise import (
    ExerciseCreateIn,
    ExerciseLogCreateIn,
    ExerciseMetricsIn,
    ExerciseOut,
    ExerciseRecordsOut,
    RecordOut,
)
from app.services.errors import DomainError

MAX_EXERCISES = 100
MAX_LOGS_PER_WORKOUT = 500


async def get_exercise(session: AsyncSession, user_id: int, exercise_id: int) -> Exercise:
    row = await session.scalar(
        select(Exercise).where(Exercise.id == exercise_id, Exercise.user_id == user_id)
    )
    if row is None:
        raise DomainError("exercise_not_found", "Exercise not found")
    return row


async def list_exercises(session: AsyncSession, user: User) -> list[Exercise]:
    return list(
        (
            await session.scalars(
                select(Exercise)
                .where(Exercise.user_id == user.id)
                .order_by(Exercise.name_key, Exercise.id)
            )
        ).all()
    )


async def lock_owner(session: AsyncSession, user: User) -> None:
    # Serializes creation/rename/limits; concurrent duplicate names become an ordinary 409.
    await session.execute(select(User.id).where(User.id == user.id).with_for_update())


async def unique_name(session: AsyncSession, user: User, name: str, exclude: int = 0) -> None:
    duplicate = await session.scalar(
        select(Exercise.id).where(
            Exercise.user_id == user.id,
            Exercise.name_key == name.casefold(),
            Exercise.id != exclude,
        )
    )
    if duplicate is not None:
        raise DomainError("exercise_exists", "An exercise with this name already exists")


async def create_exercise(session: AsyncSession, user: User, body: ExerciseCreateIn) -> Exercise:
    await lock_owner(session, user)
    await unique_name(session, user, body.name)
    count = await session.scalar(
        select(func.count()).select_from(Exercise).where(Exercise.user_id == user.id)
    )
    if count >= MAX_EXERCISES:
        raise DomainError("exercise_limit", "At most 100 exercises per account")
    row = Exercise(user_id=user.id, name=body.name, name_key=body.name.casefold(), kind=body.kind)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def rename_exercise(
    session: AsyncSession, user: User, exercise_id: int, name: str
) -> Exercise:
    await lock_owner(session, user)
    row = await get_exercise(session, user.id, exercise_id)
    await unique_name(session, user, name, exercise_id)
    row.name, row.name_key = name, name.casefold()
    await session.commit()
    await session.refresh(row)
    return row


async def delete_exercise(session: AsyncSession, user: User, exercise_id: int) -> None:
    await lock_owner(session, user)
    row = await get_exercise(session, user.id, exercise_id)
    await session.delete(row)
    await session.commit()


async def locked_workout(session: AsyncSession, user: User, workout_id: int) -> Workout:
    row = await session.scalar(
        select(Workout)
        .where(Workout.id == workout_id, Workout.user_id == user.id)
        .with_for_update()
    )
    if row is None:
        raise DomainError("workout_not_found", "Workout not found")
    if row.ended_at is None:
        raise DomainError("workout_unfinished", "Finish the workout before adding exercise results")
    return row


def validate_kind(exercise: Exercise, body: ExerciseMetricsIn) -> None:
    if (exercise.kind == "strength") != (body.weight_kg is not None):
        raise DomainError("exercise_metrics", "Metrics do not match this exercise's kind")


async def list_logs(session: AsyncSession, user: User, workout_id: int) -> list[ExerciseLog]:
    await locked_workout(session, user, workout_id)
    return list(
        (
            await session.scalars(
                select(ExerciseLog)
                .where(ExerciseLog.user_id == user.id, ExerciseLog.workout_id == workout_id)
                .order_by(ExerciseLog.id)
            )
        ).all()
    )


async def create_log(
    session: AsyncSession, user: User, workout_id: int, body: ExerciseLogCreateIn
) -> ExerciseLog:
    await lock_owner(session, user)
    workout = await locked_workout(session, user, workout_id)
    exercise = await get_exercise(session, user.id, body.exercise_id)
    validate_kind(exercise, body)
    if (
        body.duration_seconds is not None
        and body.duration_seconds > (workout.ended_at - workout.started_at).total_seconds()
    ):
        raise DomainError("exercise_time", "An effort cannot be longer than its workout")
    count = await session.scalar(
        select(func.count())
        .select_from(ExerciseLog)
        .where(ExerciseLog.user_id == user.id, ExerciseLog.workout_id == workout_id)
    )
    if count >= MAX_LOGS_PER_WORKOUT:
        raise DomainError("exercise_log_limit", "At most 500 results per workout")
    row = ExerciseLog(user_id=user.id, workout_id=workout_id, **body.model_dump())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_log(session: AsyncSession, user: User, log_id: int) -> ExerciseLog:
    row = await session.scalar(
        select(ExerciseLog).where(ExerciseLog.id == log_id, ExerciseLog.user_id == user.id)
    )
    if row is None:
        raise DomainError("exercise_log_not_found", "Exercise result not found")
    return row


async def update_log(
    session: AsyncSession, user: User, log_id: int, body: ExerciseMetricsIn
) -> ExerciseLog:
    await lock_owner(session, user)
    row = await get_log(session, user, log_id)
    workout = await locked_workout(session, user, row.workout_id)
    exercise = await get_exercise(session, user.id, row.exercise_id)
    validate_kind(exercise, body)
    if (
        body.duration_seconds is not None
        and body.duration_seconds > (workout.ended_at - workout.started_at).total_seconds()
    ):
        raise DomainError("exercise_time", "An effort cannot be longer than its workout")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_log(session: AsyncSession, user: User, log_id: int) -> None:
    await lock_owner(session, user)
    row = await get_log(session, user, log_id)
    await session.delete(row)
    await session.commit()


async def records(session: AsyncSession, user: User) -> list[ExerciseRecordsOut]:
    """Rank in PostgreSQL, sending only winners to the app. Ties use earliest date/id.

    Volume is one set (kg × reps), never an inferred 1RM. Times are compared only
    at exactly the same distance, within the same named exercise.
    """
    exercises = await list_exercises(session, user)
    grouped = {
        row.id: ExerciseRecordsOut(exercise=ExerciseOut.model_validate(row), records=[])
        for row in exercises
    }
    log = ExerciseLog
    for metric, value, condition, ascending in (
        ("weight", log.weight_kg, log.weight_kg > 0, False),
        ("reps", log.reps, log.reps.is_not(None), False),
        ("set_volume", log.weight_kg * log.reps, log.weight_kg > 0, False),
        ("distance", log.distance_m, log.distance_m.is_not(None), False),
        ("time", log.duration_seconds, log.duration_seconds.is_not(None), True),
    ):
        partition = [log.exercise_id, log.distance_m] if metric == "time" else [log.exercise_id]
        ranked = (
            select(
                log.id.label("id"),
                func.row_number()
                .over(
                    partition_by=partition,
                    order_by=[
                        value.asc() if ascending else value.desc(),
                        Workout.local_date.asc(),
                        log.id.asc(),
                    ],
                )
                .label("rank"),
            )
            .join(Workout, (Workout.id == log.workout_id) & (Workout.user_id == log.user_id))
            .where(log.user_id == user.id, Workout.ended_at.is_not(None), condition)
            .subquery()
        )
        winners = await session.execute(
            select(log, Workout.local_date, value.label("value"))
            .join(Workout, (Workout.id == log.workout_id) & (Workout.user_id == log.user_id))
            .join(ranked, ranked.c.id == log.id)
            .where(ranked.c.rank == 1)
            .order_by(log.exercise_id, log.distance_m)
        )
        for row, day, amount in winners:
            grouped[row.exercise_id].records.append(
                RecordOut(
                    metric=metric,
                    value=float(amount),
                    log_id=row.id,
                    workout_id=row.workout_id,
                    date=day,
                    weight_kg=row.weight_kg,
                    reps=row.reps,
                    distance_m=row.distance_m,
                    duration_seconds=row.duration_seconds,
                )
            )
    return list(grouped.values())
