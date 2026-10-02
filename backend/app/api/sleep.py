from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import SleepSession, User
from app.schemas.sleep import SleepSessionOut, SleepStopIn
from app.services import sleep_service

router = APIRouter(prefix="/sleep", tags=["sleep"])


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


@router.get("", response_model=list[SleepSessionOut])
async def list_sleep(
    limit: int = Query(30, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SleepSession]:
    return await sleep_service.list_sessions(session, user.id, limit)
