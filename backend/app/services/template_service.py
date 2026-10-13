from datetime import UTC, datetime

from sqlalchemy import func, select

from app.analytics.sleep_rules import local_date_of
from app.models import Exercise, ExerciseLog, Workout
from app.models.saved import WorkoutTemplate
from app.schemas.exercise import ExerciseLogCreateIn
from app.services.diary_lock import lock_diary
from app.services.errors import DomainError
from app.services.workout_service import get_running, get_workout


async def from_workout(session, user, workout_id):
    workout = await get_workout(session, user.id, workout_id)
    if workout.ended_at is None:
        raise DomainError("workout_unfinished", "Finish the source workout first")
    logs = await session.scalars(
        select(ExerciseLog)
        .where(ExerciseLog.user_id == user.id, ExerciseLog.workout_id == workout_id)
        .order_by(ExerciseLog.id)
    )
    sets = [
        ExerciseLogCreateIn.model_validate(
            {key: getattr(log, key) for key in ExerciseLogCreateIn.model_fields}
        ).model_dump(mode="json")
        for log in logs
    ]
    if not sets:
        raise DomainError("template_empty", "Add exercise results before saving a plan")
    return workout, sets


async def create(session, user, body):
    await lock_diary(session, user.id)
    count = await session.scalar(
        select(func.count()).select_from(WorkoutTemplate).where(WorkoutTemplate.user_id == user.id)
    )
    if count >= 50:
        raise DomainError("template_limit", "At most 50 saved templates")
    workout, sets = await from_workout(session, user, body.workout_id)
    row = WorkoutTemplate(
        user_id=user.id, name=body.name, type=workout.type, intensity=workout.intensity, sets=sets
    )
    session.add(row)
    await session.commit()
    return row


async def get_template(session, user, template_id):
    row = await session.scalar(
        select(WorkoutTemplate).where(
            WorkoutTemplate.user_id == user.id, WorkoutTemplate.id == template_id
        )
    )
    if row is None:
        raise DomainError("template_not_found", "Template not found")
    return row


async def start_plan(session, user, type, intensity, sets):
    if await get_running(session, user.id):
        raise DomainError("workout_running", "Finish the current workout first")
    for item in sets:
        exercise = await session.scalar(
            select(Exercise.id).where(
                Exercise.user_id == user.id, Exercise.id == item["exercise_id"]
            )
        )
        if exercise is None:
            raise DomainError(
                "template_missing_exercise",
                "Restore the deleted exercise or save an updated template",
            )
    now = datetime.now(UTC)
    row = Workout(
        user_id=user.id,
        started_at=now,
        local_date=local_date_of(now, user.timezone),
        type=type,
        intensity=intensity,
        source="template",
        planned_sets=sets,
    )
    session.add(row)
    await session.commit()
    return row


async def start_template(session, user, template_id):
    await lock_diary(session, user.id)
    row = await get_template(session, user, template_id)
    return await start_plan(session, user, row.type, row.intensity, row.sets)


async def repeat(session, user, workout_id):
    await lock_diary(session, user.id)
    workout, sets = await from_workout(session, user, workout_id)
    return await start_plan(session, user, workout.type, workout.intensity, sets)
