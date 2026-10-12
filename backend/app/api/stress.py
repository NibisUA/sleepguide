from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules
from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import StressLog, User
from app.schemas.stress import StressCreateIn, StressDayOut, StressLogOut, StressUpdateIn
from app.services import stress_service
from app.services.errors import DomainError

router = APIRouter(prefix="/stress", tags=["stress"])

HISTORY_MAX_DAYS = 366


@router.post("", response_model=StressLogOut, status_code=201)
async def create_stress(
    body: StressCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StressLog:
    return await stress_service.create_log(
        session, user, level=body.level, category=body.category, logged_at=body.logged_at
    )


@router.get("", response_model=list[StressLogOut])
async def list_stress(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[StressLog]:
    return await stress_service.list_logs(session, user.id, start, end, limit)


@router.get("/history", response_model=list[StressDayOut])
async def stress_history(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[StressDayOut]:
    """Per-day count / average / max between `from` and `to` (default: the last 30 days)."""
    today = sleep_rules.local_date_of(datetime.now(UTC), user.timezone)
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end or (end - start).days + 1 > HISTORY_MAX_DAYS:
        raise DomainError("invalid_range", f"History range must be 1–{HISTORY_MAX_DAYS} days")
    return await stress_service.history_days(session, user, start, end)


# Keep the dynamic `/{stress_id}` routes after the static ones (`/history`).
@router.get("/{stress_id}", response_model=StressLogOut)
async def get_stress(
    stress_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StressLog:
    return await stress_service.get_log(session, user.id, stress_id)


@router.patch("/{stress_id}", response_model=StressLogOut)
async def update_stress(
    stress_id: int,
    body: StressUpdateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StressLog:
    return await stress_service.update_log(
        session, user, stress_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{stress_id}", status_code=204)
async def delete_stress(
    stress_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await stress_service.delete_log(session, user, stress_id)
