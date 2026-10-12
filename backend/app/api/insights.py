from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import Insight, User
from app.schemas.insight import InsightOut, InsightsProgressOut
from app.services import insight_service

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/progress", response_model=InsightsProgressOut)
async def read_progress(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InsightsProgressOut:
    return await insight_service.progress(session, user)


@router.get("", response_model=list[InsightOut])
async def read_insights(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Insight]:
    return await insight_service.refresh(session, user)
