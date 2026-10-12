from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import api_tokens
from app.models import ApiToken, User
from app.services.errors import DomainError

MAX_ACTIVE_TOKENS = 10
LAST_USED_WRITE_INTERVAL = timedelta(minutes=1)  # do not write to the DB on every request


async def list_active(session: AsyncSession, user_id: int) -> list[ApiToken]:
    result = await session.execute(
        select(ApiToken)
        .where(ApiToken.user_id == user_id, ApiToken.revoked_at.is_(None))
        .order_by(ApiToken.created_at.desc())
    )
    return list(result.scalars())


async def create_token(
    session: AsyncSession, user: User, label: str, now: datetime | None = None
) -> tuple[ApiToken, str]:
    """Create a token. The raw secret is returned once and never stored."""
    if len(await list_active(session, user.id)) >= MAX_ACTIVE_TOKENS:
        raise DomainError("too_many_tokens", f"At most {MAX_ACTIVE_TOKENS} active tokens")
    raw = api_tokens.generate_token()
    token = ApiToken(
        user_id=user.id,
        token_hash=api_tokens.hash_token(raw),
        prefix=api_tokens.token_hint(raw),
        label=label,
        created_at=now or datetime.now(UTC),
    )
    session.add(token)
    await session.commit()
    return token, raw


async def revoke_token(
    session: AsyncSession, user: User, token_id: int, now: datetime | None = None
) -> None:
    result = await session.execute(
        select(ApiToken).where(
            ApiToken.id == token_id, ApiToken.user_id == user.id, ApiToken.revoked_at.is_(None)
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        raise DomainError("api_token_not_found", "Token not found")
    token.revoked_at = now or datetime.now(UTC)
    await session.commit()


async def authenticate(
    session: AsyncSession, raw: str, now: datetime | None = None
) -> tuple[User, ApiToken] | None:
    """Resolve a raw token to its owner; None if unknown or revoked."""
    now = now or datetime.now(UTC)
    digest = api_tokens.hash_token(raw)
    result = await session.execute(
        select(ApiToken).where(ApiToken.token_hash == digest, ApiToken.revoked_at.is_(None))
    )
    token = result.scalar_one_or_none()
    if token is None or not api_tokens.digests_match(token.token_hash, digest):
        return None
    owner = await session.execute(select(User).where(User.id == token.user_id))
    user = owner.scalar_one_or_none()
    if user is None:
        return None
    if token.last_used_at is None or now - token.last_used_at > LAST_USED_WRITE_INTERVAL:
        token.last_used_at = now
        await session.commit()
    return user, token
