from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules
from app.api.deps import get_current_user, get_user_or_api_token, record_source
from app.core.db import get_session
from app.models import ScreenTimeDaily, User
from app.schemas.screen_time import ScreenTimeIn, ScreenTimeOut
from app.services import screen_time_service
from app.services.errors import DomainError

router = APIRouter(prefix="/screen-time", tags=["screen-time"])

RANGE_MAX_DAYS = 366


@router.get("", response_model=list[ScreenTimeOut])
async def list_screen_time(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ScreenTimeDaily]:
    """Records between `from` and `to` (default: the last 30 days); days without data are absent."""
    today = sleep_rules.local_date_of(datetime.now(UTC), user.timezone)
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end or (end - start).days + 1 > RANGE_MAX_DAYS:
        raise DomainError("invalid_range", f"Range must be 1–{RANGE_MAX_DAYS} days")
    return await screen_time_service.list_range(session, user.id, start, end)


@router.put("/{day}", response_model=ScreenTimeOut)
async def put_screen_time(
    day: date,
    body: ScreenTimeIn,
    request: Request,
    user: User = Depends(get_user_or_api_token),
    session: AsyncSession = Depends(get_session),
) -> ScreenTimeDaily:
    """Idempotent upsert for one local day. Accepts a session JWT or a personal API token."""
    return await screen_time_service.upsert(
        session,
        user,
        day,
        body.total_minutes,
        body.before_bed_minutes,
        source=record_source(request),
    )


@router.delete("/{day}", status_code=204)
async def delete_screen_time(
    day: date,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await screen_time_service.delete_day(session, user, day)
