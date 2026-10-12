from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip
from app.core.config import get_settings
from app.core.db import get_session
from app.core.rate_limit import login_limiter
from app.core.security import create_access_token
from app.core.telegram_auth import InitDataError, validate_init_data
from app.schemas.auth import TelegramLoginIn, TokenOut
from app.services import user_service
from app.services.errors import DomainError

router = APIRouter(prefix="/auth", tags=["auth"])

DEV_TELEGRAM_USER_ID = 999_000_001


@router.post("/telegram", response_model=TokenOut)
async def login_with_telegram(
    body: TelegramLoginIn, request: Request, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    if not login_limiter.allow(client_ip(request)):
        raise DomainError("rate_limited", "Too many login attempts; try again later")
    settings = get_settings()
    try:
        tg_user = validate_init_data(
            body.init_data, settings.bot_token, settings.init_data_max_age_seconds
        )
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": str(exc)}) from exc
    user = await user_service.get_or_create_by_telegram_id(
        session, tg_user.id, tg_user.language_code
    )
    return TokenOut(access_token=create_access_token(user.id), user=user)


@router.post("/dev", response_model=TokenOut, include_in_schema=False)
async def dev_login(session: AsyncSession = Depends(get_session)) -> TokenOut:
    """Local development only: log in without Telegram."""
    settings = get_settings()
    if settings.env != "dev" or not settings.dev_login_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    user = await user_service.get_or_create_by_telegram_id(session, DEV_TELEGRAM_USER_ID, "uk")
    return TokenOut(access_token=create_access_token(user.id), user=user)
