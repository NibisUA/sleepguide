from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_access_token
from app.models import User

bearer = HTTPBearer(auto_error=False)


def _unauthorized(code: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": code})


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise _unauthorized("not_authenticated")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _unauthorized("invalid_token")
    user = await session.get(User, user_id)
    if user is None:
        raise _unauthorized("invalid_token")
    return user
