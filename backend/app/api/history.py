from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_snapshot_user
from app.core.db import get_snapshot_session
from app.models import User
from app.schemas.history import HistoryEntriesOut, HistoryKind, HistoryOverviewOut, HistoryRange
from app.services import history_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryOverviewOut)
async def history_overview(
    range: HistoryRange = Query("7d"),
    user: User = Depends(get_snapshot_user),
    session: AsyncSession = Depends(get_snapshot_session),
):
    return await history_service.overview(session, user, range)


@router.get("/entries/{kind}", response_model=HistoryEntriesOut)
async def history_entries(
    kind: HistoryKind,
    start: date = Query(alias="from"),
    end: date = Query(alias="to"),
    cursor: str | None = Query(None, max_length=200),
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_snapshot_user),
    session: AsyncSession = Depends(get_snapshot_session),
):
    return await history_service.entries(session, user, kind, start, end, cursor, limit)
