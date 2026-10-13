from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def lock_diary(session: AsyncSession, user_id: int) -> None:
    """Serialize diary writes with CSV validation/insertion for the same owner."""
    await session.execute(
        select(User.id).prefix_with("/* diary-write */").where(User.id == user_id).with_for_update()
    )
