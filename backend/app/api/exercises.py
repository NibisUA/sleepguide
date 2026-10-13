from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_snapshot_user
from app.core.db import get_session, get_snapshot_session
from app.models import User
from app.schemas.exercise import (
    ExerciseBatchIn,
    ExerciseCreateIn,
    ExerciseLogCreateIn,
    ExerciseLogOut,
    ExerciseMetricsIn,
    ExerciseOut,
    ExerciseRecordsOut,
    ExerciseRenameIn,
)
from app.services import exercise_service as service

router = APIRouter(tags=["exercises"])


@router.get("/exercises", response_model=list[ExerciseOut])
async def list_exercises(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await service.list_exercises(session, user)


@router.post("/exercises", response_model=ExerciseOut, status_code=201)
async def create_exercise(
    body: ExerciseCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.create_exercise(session, user, body)


@router.patch("/exercises/{exercise_id}", response_model=ExerciseOut)
async def rename_exercise(
    exercise_id: int,
    body: ExerciseRenameIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.rename_exercise(session, user, exercise_id, body.name)


@router.delete("/exercises/{exercise_id}", status_code=204)
async def delete_exercise(
    exercise_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await service.delete_exercise(session, user, exercise_id)


@router.get("/records", response_model=list[ExerciseRecordsOut])
async def get_records(
    user: User = Depends(get_snapshot_user), session: AsyncSession = Depends(get_snapshot_session)
):
    return await service.records(session, user)


@router.get("/workouts/{workout_id}/exercises", response_model=list[ExerciseLogOut])
async def list_logs(
    workout_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.list_logs(session, user, workout_id)


@router.post("/workouts/{workout_id}/exercises", response_model=ExerciseLogOut, status_code=201)
async def create_log(
    workout_id: int,
    body: ExerciseLogCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.create_log(session, user, workout_id, body)


@router.put("/exercise-logs/{log_id}", response_model=ExerciseLogOut)
async def update_log(
    log_id: int,
    body: ExerciseMetricsIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.update_log(session, user, log_id, body)


@router.post(
    "/workouts/{workout_id}/exercises/batch", response_model=list[ExerciseLogOut], status_code=201
)
async def create_sets(
    body: ExerciseBatchIn,
    workout_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.create_sets(session, user, workout_id, body.sets)


@router.delete("/exercise-logs/{log_id}", status_code=204)
async def delete_log(
    log_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await service.delete_log(session, user, log_id)
