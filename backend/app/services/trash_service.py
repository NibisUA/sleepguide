"""Snapshots are saved in the same transaction as deletion, never client supplied."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, delete, func, inspect, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Exercise,
    ExerciseLog,
    ScreenTimeDaily,
    SleepSession,
    StressLog,
    User,
    Workout,
)
from app.models.saved import DeletedEntry
from app.services.diary_lock import lock_diary
from app.services.errors import DomainError

MODELS = {
    "sleep": SleepSession,
    "workout": Workout,
    "stress": StressLog,
    "screen": ScreenTimeDaily,
    "exercise": Exercise,
    "exercise_log": ExerciseLog,
}


def encode_row(row):
    return {
        column.key: (
            value.isoformat()
            if isinstance(value, (datetime, date))
            else str(value)
            if isinstance(value, Decimal)
            else value
        )
        for column in inspect(type(row)).columns
        for value in [getattr(row, column.key)]
    }


def decode_row(model, data):
    values = dict(data)
    for column in inspect(model).columns:
        value = values.get(column.key)
        if value is not None:
            if isinstance(column.type, DateTime):
                values[column.key] = datetime.fromisoformat(value)
            elif isinstance(column.type, Date):
                values[column.key] = date.fromisoformat(value)
            elif isinstance(column.type, Numeric):
                values[column.key] = Decimal(value)
    return values


async def archive(session: AsyncSession, user_id: int, kind: str, row) -> None:
    children = []
    if kind in ("workout", "exercise"):
        key = ExerciseLog.workout_id if kind == "workout" else ExerciseLog.exercise_id
        result = await session.execute(
            select(ExerciseLog).where(ExerciseLog.user_id == user_id, key == row.id)
        )
        children = [encode_row(child) for child in result.scalars()]
    stamp = getattr(row, "local_date", None) or getattr(row, "started_at", None) or ""
    label = row.name if kind == "exercise" else str(stamp)
    if kind == "exercise_log":
        label = f"#{row.workout_id}: {row.reps or row.distance_m}"
    now = datetime.now(UTC)
    session.add(
        DeletedEntry(
            user_id=user_id,
            kind=kind,
            label=label[:160],
            payload={"row": encode_row(row), "children": children},
            deleted_at=now,
            expires_at=now + timedelta(days=30),
        )
    )


async def purge_expired(session: AsyncSession, user_id: int):
    await session.execute(
        delete(DeletedEntry).where(
            DeletedEntry.user_id == user_id, DeletedEntry.expires_at <= datetime.now(UTC)
        )
    )


async def list_deleted(session: AsyncSession, user: User):
    await purge_expired(session, user.id)
    result = await session.execute(
        select(DeletedEntry)
        .where(DeletedEntry.user_id == user.id)
        .order_by(DeletedEntry.deleted_at.desc(), DeletedEntry.id.desc())
        .limit(200)
    )
    rows = list(result.scalars())
    await session.commit()
    return rows


async def get_deleted(session, user, entry_id):
    row = await session.scalar(
        select(DeletedEntry)
        .where(
            DeletedEntry.user_id == user.id,
            DeletedEntry.id == entry_id,
            DeletedEntry.expires_at > datetime.now(UTC),
        )
        .with_for_update()
    )
    if row is None:
        raise DomainError("deleted_not_found", "Deleted entry is missing or expired")
    return row


async def validate_log(session, user, data):
    workout = await session.scalar(
        select(Workout).where(Workout.user_id == user.id, Workout.id == data["workout_id"])
    )
    exercise = await session.scalar(
        select(Exercise).where(Exercise.user_id == user.id, Exercise.id == data["exercise_id"])
    )
    if workout is None or exercise is None:
        raise DomainError("restore_conflict", "Restore the parent workout and exercise first")
    count = await session.scalar(
        select(func.count())
        .select_from(ExerciseLog)
        .where(ExerciseLog.user_id == user.id, ExerciseLog.workout_id == workout.id)
    )
    if count >= 500 or (
        data["duration_seconds"] is not None
        and data["duration_seconds"]
        > ((workout.ended_at or datetime.now(UTC)) - workout.started_at).total_seconds()
    ):
        raise DomainError("restore_conflict", "The current workout cannot contain this result")


async def restore(session: AsyncSession, user: User, entry_id: int):
    await lock_diary(session, user.id)
    entry = await get_deleted(session, user, entry_id)
    model = MODELS[entry.kind]
    data = decode_row(model, entry.payload["row"])
    # Payloads are created internally; still enforce owner on every restored row.
    data["user_id"] = user.id
    if entry.kind in ("sleep", "workout"):
        end = data["ended_at"]
        query = select(model.id).where(
            model.user_id == user.id,
            or_(model.ended_at.is_(None), model.ended_at > data["started_at"]),
        )
        if end is not None:
            query = query.where(model.started_at < end)
        if await session.scalar(query.limit(1)) is not None:
            raise DomainError("restore_conflict", "This interval overlaps a current entry")
    if entry.kind == "exercise":
        count = await session.scalar(
            select(func.count()).select_from(Exercise).where(Exercise.user_id == user.id)
        )
        if count >= 100:
            raise DomainError("restore_conflict", "Exercise limit reached")
    if entry.kind == "exercise_log":
        await validate_log(session, user, data)
    try:
        session.add(model(**data))
        await session.flush()
        for child in entry.payload["children"]:
            child_data = decode_row(ExerciseLog, child)
            child_data["user_id"] = user.id
            await validate_log(session, user, child_data)
            session.add(ExerciseLog(**child_data))
            await session.flush()
        await session.delete(entry)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DomainError(
            "restore_conflict", "A current entry or missing parent prevents restoration"
        ) from exc
    except DomainError:
        await session.rollback()
        raise


async def erase(session, user, entry_id):
    await lock_diary(session, user.id)
    entry = await get_deleted(session, user, entry_id)
    await session.delete(entry)
    await session.commit()
