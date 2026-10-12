from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules
from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.schemas.day import DaySummaryOut
from app.services import day_service
from app.services.errors import DomainError

router = APIRouter(prefix="/days", tags=["days"])


@router.get("/{day}", response_model=DaySummaryOut)
async def get_day(
    day: date,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DaySummaryOut:
    """Daily Summary: sleep + workouts + stress + screen time for one local day (not the future)."""
    today = sleep_rules.local_date_of(datetime.now(UTC), user.timezone)
    if day > today:
        raise DomainError("invalid_date", "The day cannot be in the future")
    return await day_service.build_summary(session, user, day)
