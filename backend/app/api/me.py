from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_export_user
from app.core.db import get_session, get_snapshot_session
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.privacy import DataExportOut, DeleteMeIn
from app.schemas.user import UserUpdate
from app.services import privacy_service

router = APIRouter(prefix="/me", tags=["me"])

NULLABLE_FIELDS = {"target_bedtime", "reminder_evening_time"}


@router.get("", response_model=UserOut)
async def read_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/export", response_model=DataExportOut)
async def export_me(
    response: Response,
    user: User = Depends(get_export_user),
    session: AsyncSession = Depends(get_snapshot_session),
) -> DataExportOut:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="sleepguide-export-{datetime.now(UTC):%Y-%m-%d}.json"'
    )
    return await privacy_service.export_data(session, user)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    body: DeleteMeIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await privacy_service.delete_account(session, user)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.patch("", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    for field, value in body.model_dump(exclude_unset=True).items():
        # `null` is meaningful only for these fields (it clears the value)
        if value is not None or field in NULLABLE_FIELDS:
            setattr(user, field, value)
    await session.commit()
    return user
