from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules
from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import SleepSession, User
from app.schemas.sleep import (
    SleepCreateIn,
    SleepDayOut,
    SleepScoreOut,
    SleepSessionOut,
    SleepStopIn,
    SleepUpdateIn,
)
from app.services import sleep_service
from app.services.errors import DomainError

router = APIRouter(prefix="/sleep", tags=["sleep"])

HISTORY_MAX_DAYS = 366


@router.post("/start", response_model=SleepSessionOut)
async def start_sleep(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> SleepSession:
    return await sleep_service.start_sleep(session, user)


@router.post("/stop", response_model=SleepSessionOut)
async def stop_sleep(
    body: SleepStopIn | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SleepSession:
    return await sleep_service.stop_sleep(session, user, ended_at=body.ended_at if body else None)


@router.get("/current", response_model=SleepSessionOut | None)
async def current_sleep(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> SleepSession | None:
    return await sleep_service.get_open_session(session, user.id)


@router.get("/history", response_model=list[SleepDayOut])
async def sleep_history(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SleepDayOut]:
    """Daily summaries between `from` and `to` (default: the last 30 days)."""
    today = sleep_rules.local_date_of(datetime.now(UTC), user.timezone)
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end or (end - start).days + 1 > HISTORY_MAX_DAYS:
        raise DomainError("invalid_range", f"History range must be 1–{HISTORY_MAX_DAYS} days")
    days = await sleep_service.history_days(session, user, start, end)
    return [SleepDayOut.model_validate(day) for day in days]


@router.get("/score/{target_date}", response_model=SleepScoreOut | None)
async def sleep_score(
    target_date: date,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SleepScoreOut | None:
    """Sleep Score for the night that ended on `target_date` (null if none)."""
    score = await sleep_service.score_for_date(session, user, target_date)
    return SleepScoreOut.model_validate(score) if score else None


@router.post("", response_model=SleepSessionOut, status_code=201)
async def create_sleep(
    body: SleepCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SleepSession:
    return await sleep_service.create_session(
        session, user, started_at=body.started_at, ended_at=body.ended_at
    )


@router.get("", response_model=list[SleepSessionOut])
async def list_sleep(
    limit: int = Query(30, ge=1, le=200),
    on_date: date | None = Query(None, alias="date"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SleepSession]:
    return await sleep_service.list_sessions(session, user.id, limit, on_date)


# Keep the dynamic `/{sleep_id}` routes after the static ones (`/current`, `/score/...`).
@router.get("/{sleep_id}", response_model=SleepSessionOut)
async def get_sleep(
    sleep_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SleepSession:
    return await sleep_service.get_session(session, user.id, sleep_id)


@router.patch("/{sleep_id}", response_model=SleepSessionOut)
async def update_sleep(
    sleep_id: int,
    body: SleepUpdateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SleepSession:
    data = body.model_dump(exclude_unset=True)
    return await sleep_service.update_session(
        session,
        user,
        sleep_id,
        started_at=data.get("started_at"),
        ended_at=data.get("ended_at"),
    )


@router.delete("/{sleep_id}", status_code=204)
async def delete_sleep(
    sleep_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await sleep_service.delete_session(session, user, sleep_id)
