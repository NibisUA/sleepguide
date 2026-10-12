from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules
from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import User, Workout
from app.schemas.workout import (
    WorkoutCreateIn,
    WorkoutDayOut,
    WorkoutOut,
    WorkoutStartIn,
    WorkoutStopIn,
    WorkoutUpdateIn,
)
from app.services import workout_service
from app.services.errors import DomainError

router = APIRouter(prefix="/workouts", tags=["workouts"])

HISTORY_MAX_DAYS = 366


@router.post("/start", response_model=WorkoutOut)
async def start_workout(
    body: WorkoutStartIn | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    body = body or WorkoutStartIn()
    return await workout_service.start_workout(session, user, body.type, body.intensity)


@router.post("/stop", response_model=WorkoutOut)
async def stop_workout(
    body: WorkoutStopIn | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    body = body or WorkoutStopIn()
    return await workout_service.stop_workout(
        session, user, ended_at=body.ended_at, type=body.type, intensity=body.intensity
    )


@router.get("/current", response_model=WorkoutOut | None)
async def current_workout(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> Workout | None:
    return await workout_service.get_running(session, user.id)


@router.get("/history", response_model=list[WorkoutDayOut])
async def workout_history(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[WorkoutDayOut]:
    """Per-day count and minutes between `from` and `to` (default: the last 30 days)."""
    today = sleep_rules.local_date_of(datetime.now(UTC), user.timezone)
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end or (end - start).days + 1 > HISTORY_MAX_DAYS:
        raise DomainError("invalid_range", f"History range must be 1–{HISTORY_MAX_DAYS} days")
    return await workout_service.history_days(session, user, start, end)


@router.post("", response_model=WorkoutOut, status_code=201)
async def create_workout(
    body: WorkoutCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    return await workout_service.create_workout(
        session,
        user,
        started_at=body.started_at,
        ended_at=body.ended_at,
        type=body.type,
        intensity=body.intensity,
    )


@router.get("", response_model=list[WorkoutOut])
async def list_workouts(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Workout]:
    return await workout_service.list_workouts(session, user.id, start, end, limit)


# Keep the dynamic `/{workout_id}` routes after the static ones (`/current`, `/history`, ...).
@router.get("/{workout_id}", response_model=WorkoutOut)
async def get_workout(
    workout_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    return await workout_service.get_workout(session, user.id, workout_id)


@router.patch("/{workout_id}", response_model=WorkoutOut)
async def update_workout(
    workout_id: int,
    body: WorkoutUpdateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    data = body.model_dump(exclude_unset=True)
    return await workout_service.update_workout(
        session,
        user,
        workout_id,
        started_at=data.get("started_at"),
        ended_at=data.get("ended_at"),
        type=data.get("type"),
        intensity=data.get("intensity"),
    )


@router.delete("/{workout_id}", status_code=204)
async def delete_workout(
    workout_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await workout_service.delete_workout(session, user, workout_id)
