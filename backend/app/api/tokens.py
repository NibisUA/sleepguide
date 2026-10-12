from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user  # JWT only: tokens can never manage tokens
from app.core.db import get_session
from app.models import ApiToken, User
from app.schemas.api_token import ApiTokenCreatedOut, ApiTokenCreateIn, ApiTokenOut
from app.services import api_token_service

router = APIRouter(prefix="/me/api-tokens", tags=["api-tokens"])


@router.post("", response_model=ApiTokenCreatedOut, status_code=201)
async def create_api_token(
    body: ApiTokenCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiTokenCreatedOut:
    token, raw = await api_token_service.create_token(session, user, body.label)
    return ApiTokenCreatedOut(**ApiTokenOut.model_validate(token).model_dump(), token=raw)


@router.get("", response_model=list[ApiTokenOut])
async def list_api_tokens(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[ApiToken]:
    return await api_token_service.list_active(session, user.id)


@router.delete("/{token_id}", status_code=204)
async def revoke_api_token(
    token_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await api_token_service.revoke_token(session, user, token_id)
