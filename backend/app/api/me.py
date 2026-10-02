from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.user import UserUpdate

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
async def read_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    await session.commit()
    return user
