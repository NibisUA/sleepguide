from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules, workout_rules
from app.models import ExerciseLog, User, Workout
from app.schemas.workout import WorkoutDayOut
from app.services.errors import DomainError


async def get_running(session: AsyncSession, user_id: int) -> Workout | None:
    result = await session.execute(
        select(Workout).where(Workout.user_id == user_id, Workout.ended_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_workout(
    session: AsyncSession, user_id: int, workout_id: int, lock: bool = False
) -> Workout:
    statement = select(Workout).where(Workout.id == workout_id, Workout.user_id == user_id)
    result = await session.execute(statement.with_for_update() if lock else statement)
    workout = result.scalar_one_or_none()
    if workout is None:
        raise DomainError("workout_not_found", "Workout not found")
    return workout


def _validate_completed(started_at: datetime, ended_at: datetime, now: datetime) -> None:
    if started_at > now + sleep_rules.MAX_FUTURE_SKEW:
        raise DomainError("invalid_time", "A workout cannot start in the future")
    if not sleep_rules.is_valid_end(started_at, ended_at, now):
        raise DomainError("invalid_time", "The end must be after the start and not in the future")
    if sleep_rules.duration_minutes(started_at, ended_at) < 1:
        raise DomainError("invalid_time", "A workout must last at least a minute")
    if workout_rules.is_too_long(started_at, ended_at):
        raise DomainError("too_long", "A workout cannot be longer than 6 hours")


async def _has_overlap(
    session: AsyncSession,
    user_id: int,
    started_at: datetime,
    ended_at: datetime,
    exclude_id: int | None = None,
) -> bool:
    statement = select(Workout.id).where(
        Workout.user_id == user_id,
        Workout.started_at < ended_at,
        # A running workout has no end yet, so it overlaps anything that ends after it started.
        or_(Workout.ended_at.is_(None), Workout.ended_at > started_at),
    )
    if exclude_id is not None:
        statement = statement.where(Workout.id != exclude_id)
    result = await session.execute(statement.limit(1))
    return result.scalar_one_or_none() is not None


def _apply_completed(
    workout: Workout, user: User, started_at: datetime, ended_at: datetime
) -> None:
    workout.started_at = started_at
    workout.ended_at = ended_at
    workout.duration_minutes = sleep_rules.duration_minutes(started_at, ended_at)
    workout.local_date = sleep_rules.local_date_of(started_at, user.timezone)


async def start_workout(
    session: AsyncSession,
    user: User,
    type: str = workout_rules.DEFAULT_TYPE,
    intensity: str = workout_rules.DEFAULT_INTENSITY,
    source: str = "manual",
    now: datetime | None = None,
) -> Workout:
    """Start a workout. Idempotent: if one is already running, return it."""
    existing = await get_running(session, user.id)
    if existing:
        return existing
    now = now or datetime.now(UTC)
    workout = Workout(
        user_id=user.id,
        started_at=now,
        local_date=sleep_rules.local_date_of(now, user.timezone),
        type=type,
        intensity=intensity,
        source=source,
    )
    session.add(workout)
    try:
        await session.commit()
    except IntegrityError:  # race with a concurrent start
        await session.rollback()
        existing = await get_running(session, user.id)
        if existing is None:
            raise
        return existing
    return workout


async def stop_workout(
    session: AsyncSession,
    user: User,
    ended_at: datetime | None = None,
    type: str | None = None,
    intensity: str | None = None,
    now: datetime | None = None,
) -> Workout:
    """Finish the running workout (type / intensity may be corrected at the same time).

    A workout that has run for more than 6 hours needs an explicit end time: the client must
    ask the user when they actually finished.
    """
    now = now or datetime.now(UTC)
    workout = await get_running(session, user.id)
    if workout is None:
        raise DomainError("no_running_workout", "There is no workout to finish")

    if ended_at is None:
        if workout_rules.needs_end_time(workout.started_at, now):
            raise DomainError("end_time_required", "The workout is too old; specify the end time")
        ended_at = now
    _validate_completed(workout.started_at, ended_at, now)

    _apply_completed(workout, user, workout.started_at, ended_at)
    if type is not None:
        workout.type = type
    if intensity is not None:
        workout.intensity = intensity
    await session.commit()
    return workout


async def create_workout(
    session: AsyncSession,
    user: User,
    started_at: datetime,
    ended_at: datetime,
    type: str,
    intensity: str,
    now: datetime | None = None,
) -> Workout:
    """Retroactive entry: a completed workout the user logged after the fact."""
    now = now or datetime.now(UTC)
    _validate_completed(started_at, ended_at, now)
    if await _has_overlap(session, user.id, started_at, ended_at):
        raise DomainError("overlap", "This interval overlaps another workout")

    workout = Workout(user_id=user.id, type=type, intensity=intensity, source="retro")
    _apply_completed(workout, user, started_at, ended_at)
    session.add(workout)
    await session.commit()
    return workout


async def update_workout(
    session: AsyncSession,
    user: User,
    workout_id: int,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    type: str | None = None,
    intensity: str | None = None,
    now: datetime | None = None,
) -> Workout:
    """Partial edit (`None` keeps the current value).

    Giving a running workout an end time finishes it; a finished workout is never reopened.
    """
    now = now or datetime.now(UTC)
    workout = await get_workout(session, user.id, workout_id, lock=True)
    new_start = started_at or workout.started_at
    new_end = ended_at or workout.ended_at

    if new_end is None:  # still running: only the start (and type / intensity) can change
        if new_start > now + sleep_rules.MAX_FUTURE_SKEW:
            raise DomainError("invalid_time", "A workout cannot start in the future")
        if await _has_overlap(session, user.id, new_start, now, exclude_id=workout.id):
            raise DomainError("overlap", "This interval overlaps another workout")
        workout.started_at = new_start
        workout.local_date = sleep_rules.local_date_of(new_start, user.timezone)
    else:
        _validate_completed(new_start, new_end, now)
        if workout.ended_at is not None and (new_end - new_start) < (
            workout.ended_at - workout.started_at
        ):
            too_long = await session.execute(
                select(ExerciseLog.id)
                .where(
                    ExerciseLog.user_id == user.id,
                    ExerciseLog.workout_id == workout.id,
                    ExerciseLog.duration_seconds > (new_end - new_start).total_seconds(),
                )
                .limit(1)
            )
            if too_long.scalar_one_or_none() is not None:
                raise DomainError("exercise_time", "Edit the longer exercise result first")
        if await _has_overlap(session, user.id, new_start, new_end, exclude_id=workout.id):
            raise DomainError("overlap", "This interval overlaps another workout")
        _apply_completed(workout, user, new_start, new_end)

    if type is not None:
        workout.type = type
    if intensity is not None:
        workout.intensity = intensity
    await session.commit()
    return workout


async def delete_workout(session: AsyncSession, user: User, workout_id: int) -> None:
    workout = await get_workout(session, user.id, workout_id, lock=True)
    await session.delete(workout)
    await session.commit()


async def list_workouts(
    session: AsyncSession,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
) -> list[Workout]:
    statement = select(Workout).where(Workout.user_id == user_id)
    if start_date is not None:
        statement = statement.where(Workout.local_date >= start_date)
    if end_date is not None:
        statement = statement.where(Workout.local_date <= end_date)
    result = await session.execute(statement.order_by(Workout.started_at.desc()).limit(limit))
    return list(result.scalars())


async def history_days(
    session: AsyncSession, user: User, start_date: date, end_date: date
) -> list[WorkoutDayOut]:
    """Per-day workout count and minutes for ``[start_date, end_date]`` (every day is included)."""
    result = await session.execute(
        select(Workout).where(
            Workout.user_id == user.id,
            Workout.ended_at.is_not(None),
            Workout.local_date >= start_date,
            Workout.local_date <= end_date,
        )
    )
    counts: dict[date, int] = defaultdict(int)
    minutes: dict[date, int] = defaultdict(int)
    for row in result.scalars():
        counts[row.local_date] += 1
        minutes[row.local_date] += row.duration_minutes or 0

    return [
        WorkoutDayOut(date=day, count=counts[day], minutes=minutes[day])
        for day in (
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        )
    ]
