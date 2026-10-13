from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.models.saved import WorkoutTemplate
from app.schemas.saved import DeletedOut, TemplateCreateIn, TemplateOut
from app.schemas.workout import WorkoutOut
from app.services import template_service, trash_service
from app.services.diary_lock import lock_diary

router = APIRouter(tags=["saved"])


@router.get("/workout-templates", response_model=list[TemplateOut])
async def templates(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return list(
        await session.scalars(
            select(WorkoutTemplate)
            .where(WorkoutTemplate.user_id == user.id)
            .order_by(WorkoutTemplate.id.desc())
        )
    )


@router.post("/workout-templates", response_model=TemplateOut, status_code=201)
async def create_template(
    body: TemplateCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await template_service.create(session, user, body)


@router.delete("/workout-templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await lock_diary(session, user.id)
    row = await template_service.get_template(session, user, template_id)
    await session.delete(row)
    await session.commit()


@router.post("/workout-templates/{template_id}/start", response_model=WorkoutOut)
async def start_template(
    template_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await template_service.start_template(session, user, template_id)


@router.post("/workouts/{workout_id}/repeat", response_model=WorkoutOut)
async def repeat_workout(
    workout_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await template_service.repeat(session, user, workout_id)


@router.get("/trash", response_model=list[DeletedOut])
async def trash(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await trash_service.list_deleted(session, user)


@router.post("/trash/{entry_id}/restore", status_code=204)
async def restore(
    entry_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await trash_service.restore(session, user, entry_id)


@router.delete("/trash/{entry_id}", status_code=204)
async def erase(
    entry_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await trash_service.erase(session, user, entry_id)
