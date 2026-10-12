from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_snapshot_user
from app.core.db import get_session, get_snapshot_session
from app.models import SleepFeedback, User
from app.schemas.personal import (
    BaselinesOut,
    CalibrationOut,
    FeedbackIn,
    FeedbackOut,
    MilestonesOut,
)
from app.services import personal_service

router = APIRouter(prefix="/personal", tags=["personal"])


@router.get("/baselines", response_model=BaselinesOut)
async def get_baselines(
    user: User = Depends(get_snapshot_user), session: AsyncSession = Depends(get_snapshot_session)
):
    return await personal_service.get_baselines(session, user)


@router.get("/milestones", response_model=MilestonesOut)
async def get_milestones(
    user: User = Depends(get_snapshot_user), session: AsyncSession = Depends(get_snapshot_session)
):
    return await personal_service.milestones(session, user)


@router.get("/calibration", response_model=CalibrationOut)
async def get_calibration(
    user: User = Depends(get_snapshot_user), session: AsyncSession = Depends(get_snapshot_session)
):
    return await personal_service.calibration(session, user)


@router.get("/feedback/{day}", response_model=FeedbackOut | None)
async def get_feedback(
    day: date, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await personal_service.feedback_for_date(session, user, day)


@router.put("/feedback/{day}", response_model=FeedbackOut)
async def save_feedback(
    day: date,
    body: FeedbackIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await personal_service.put_feedback(session, user, day, body.rating)


@router.delete("/feedback/{day}", status_code=204)
async def delete_feedback(
    day: date, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    await session.execute(
        delete(SleepFeedback).where(
            SleepFeedback.user_id == user.id, SleepFeedback.local_date == day
        )
    )
    await session.commit()
    return Response(status_code=204)
