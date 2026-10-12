from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import api_tokens, rate_limit
from app.core.config import get_settings
from app.core.db import get_session, get_snapshot_session
from app.core.security import decode_access_token
from app.models import User
from app.services import api_token_service
from app.services.errors import DomainError

bearer = HTTPBearer(auto_error=False)


def _unauthorized(code: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": code})


async def _user_from_jwt(session: AsyncSession, token: str) -> User:
    user_id = decode_access_token(token)
    if user_id is None:
        raise _unauthorized("invalid_token")
    user = await session.get(User, user_id)
    if user is None:
        raise _unauthorized("invalid_token")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Mini App session (JWT) only. Personal API tokens are NOT accepted here, so a leaked
    Shortcut token cannot read data or manage tokens: it works only on the endpoints that use
    `get_user_or_api_token` below (sleep start/stop and Screen Time upsert)."""
    if credentials is None:
        raise _unauthorized("not_authenticated")
    return await _user_from_jwt(session, credentials.credentials)


async def get_export_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_snapshot_session),
) -> User:
    if credentials is None:
        raise _unauthorized("not_authenticated")
    return await _user_from_jwt(session, credentials.credentials)


# The same JWT lookup and connection are used for consistent multi-query reads.
get_snapshot_user = get_export_user


def client_ip(request: Request) -> str:
    # Trust forwarding only from the configured reverse proxy; direct callers
    # cannot select a new rate-limit bucket by inventing X-Forwarded-For.
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and peer in get_settings().trusted_proxy_ips:
        return forwarded.split(",")[-1].strip()
    return peer


async def get_user_or_api_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Mini App session (JWT) or a personal API token (iOS Shortcuts)."""
    if credentials is None:
        raise _unauthorized("not_authenticated")
    raw = credentials.credentials
    if not api_tokens.looks_like_api_token(raw):
        request.state.auth_source = "jwt"
        return await _user_from_jwt(session, raw)

    ip = client_ip(request)
    if rate_limit.failed_auth_limiter.is_blocked(ip):
        raise DomainError("rate_limited", "Too many failed attempts, try again later")
    found = await api_token_service.authenticate(session, raw)
    if found is None:
        rate_limit.failed_auth_limiter.hit(ip)
        raise _unauthorized("invalid_token")
    user, token = found
    if not rate_limit.token_usage_limiter.allow(str(token.id)):
        raise DomainError("rate_limited", "Too many requests with this token")
    request.state.auth_source = "token"
    return user


def record_source(request: Request) -> str:
    """ "shortcut" for a request authenticated with an API token, "manual" otherwise."""
    return "shortcut" if getattr(request.state, "auth_source", "jwt") == "token" else "manual"
