from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


def language_from_telegram(language_code: str | None) -> str:
    return "uk" if (language_code or "").lower().startswith("uk") else "en"


async def get_or_create_by_telegram_id(
    session: AsyncSession, telegram_user_id: int, language_code: str | None
) -> User:
    async def _find() -> User | None:
        result = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        return result.scalar_one_or_none()

    user = await _find()
    if user:
        return user
    user = User(telegram_user_id=telegram_user_id, language=language_from_telegram(language_code))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:  # concurrent first login
        await session.rollback()
        existing = await _find()
        if existing is None:
            raise
        return existing
    return user
