from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_snapshot_user
from app.core.db import get_snapshot_session
from app.models import User
from app.schemas.progress import ProgressOut
from app.services.progress_service import progress

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
async def get_progress(
    user: User = Depends(get_snapshot_user), session: AsyncSession = Depends(get_snapshot_session)
) -> ProgressOut:
    return await progress(session, user)
