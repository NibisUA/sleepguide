from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.sleep_rules import local_date_of
from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.models.study import StudyEvent, StudyPlan
from app.schemas.study import (
    StudyCheckIn,
    StudyEventOut,
    StudyParseIn,
    StudyPlanIn,
    StudyPlanOut,
    StudyReplanIn,
)
from app.services import study_service as service
from app.services.errors import DomainError
from app.services.study_parser import parse_text

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/parse")
async def parse(body: StudyParseIn, user: User = Depends(get_current_user)):
    return parse_text(body.text, body.year)


@router.get("/plans", response_model=list[StudyPlanOut])
async def plans(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return list(
        await session.scalars(
            select(StudyPlan)
            .where(StudyPlan.user_id == user.id)
            .order_by(StudyPlan.deadline, StudyPlan.id)
        )
    )


@router.post("/plans", response_model=StudyPlanOut, status_code=201)
async def create(
    body: StudyPlanIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.save_plan(session, user, body)


@router.post("/preview")
async def preview(
    body: StudyPlanIn,
    plan_id: int | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    today = local_date_of(datetime.now(UTC), user.timezone)
    start = body.start_date or today
    if start > body.deadline:
        raise DomainError("study_invalid", "Початок не може бути після дедлайну")
    old = {}
    if plan_id is not None:
        plan = await service.get_plan(session, user, plan_id)
        service.check_version(plan, body.expected_version)
        old = {row["label"]: row for row in plan.items}
    items = service.prepare_items(body, old, today, start)
    return dict(
        items=items,
        working_days=len(service.working_days(max(today, start), body.deadline, body.reserve_days)),
    )


@router.put("/plans/{plan_id}", response_model=StudyPlanOut)
async def update(
    plan_id: int,
    body: StudyPlanIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.save_plan(session, user, body, plan_id)


@router.post("/plans/{plan_id}/items/{label}", response_model=StudyPlanOut)
async def check(
    plan_id: int,
    label: str,
    body: StudyCheckIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.check_item(session, user, plan_id, label, body)


@router.get("/plans/{plan_id}/replan-preview")
async def replan_preview(
    plan_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    plan = await service.get_plan(session, user, plan_id)
    today = local_date_of(datetime.now(UTC), user.timezone)
    return dict(
        expected_version=plan.version,
        assignments=service.allocate(
            plan.items, max(today, plan.start_date), plan.deadline, plan.reserve_days
        ),
        summary=service.summary(plan, today),
    )


@router.post("/plans/{plan_id}/schedule", response_model=StudyPlanOut)
async def schedule(
    plan_id: int,
    body: StudyReplanIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.apply_schedule(session, user, plan_id, body)


@router.get("/plans/{plan_id}/events", response_model=list[StudyEventOut])
async def events(
    plan_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await service.get_plan(session, user, plan_id)
    return list(
        await session.scalars(
            select(StudyEvent)
            .where(StudyEvent.user_id == user.id, StudyEvent.plan_id == plan_id)
            .order_by(StudyEvent.id.desc())
            .limit(500)
        )
    )
