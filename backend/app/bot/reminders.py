"""Background reminder loop (evening "go to bed" and morning "I woke up" nudges).

Runs inside the FastAPI process (see `main.py` lifespan). The API is deployed as a single
process on a single VM, so only one loop exists; sends are still claimed with an atomic UPDATE,
so overlapping ticks or a restart never produce duplicates.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import reminders
from app.analytics.personal import bedtime_pattern
from app.analytics.sleep_rules import local_date_of
from app.bot import actions, texts
from app.core.db import SessionLocal
from app.models import SleepSession, User
from app.services.sleep_service import _to_night

logger = logging.getLogger(__name__)

TICK_SECONDS = 60
SEND_DELAY_SECONDS = 0.05  # ~20 messages/s, below Telegram's broadcast limit


async def _claim_evening(session: AsyncSession, user_id: int, day: date) -> bool:
    result = await session.execute(
        update(User)
        .where(
            User.id == user_id,
            or_(User.last_evening_reminder_date.is_(None), User.last_evening_reminder_date != day),
        )
        .values(last_evening_reminder_date=day)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount == 1


async def _claim_morning(
    session: AsyncSession, user_id: int, started_at: datetime, now: datetime
) -> bool:
    result = await session.execute(
        update(User)
        .where(
            User.id == user_id,
            or_(
                User.last_morning_reminder_at.is_(None), User.last_morning_reminder_at < started_at
            ),
        )
        .values(last_morning_reminder_at=now)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount == 1


async def _disable_reminders(session: AsyncSession, user_id: int) -> None:
    """The user blocked the bot (or the chat does not exist): stop trying."""
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(reminder_evening_time=None, reminder_morning_on=False, reminder_pattern_on=False)
        .execution_options(synchronize_session=False)
    )
    await session.commit()


async def _deliver(session: AsyncSession, bot: Bot, user: User, kind: str) -> bool:
    lang = texts.lang_of(user.language)
    callback = actions.CB_START if kind == "evening" else actions.CB_STOP
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.text(lang, f"{kind}_button"), callback_data=callback)]
        ]
    )
    try:
        await bot.send_message(
            user.telegram_user_id,
            texts.text(lang, kind),
            reply_markup=keyboard,
            disable_notification=(kind == "morning"),  # a silent nudge must not wake anyone
        )
    except TelegramForbiddenError:
        await _disable_reminders(session, user.id)
        return False
    except TelegramBadRequest as exc:
        if "chat not found" in str(exc).lower():
            await _disable_reminders(session, user.id)
        else:
            logger.warning("Reminder rejected by Telegram for user %s: %s", user.id, exc)
        return False
    except TelegramRetryAfter as exc:
        logger.warning("Telegram asked to slow down for %s s", exc.retry_after)
        await asyncio.sleep(min(exc.retry_after, 30))
        return False
    await asyncio.sleep(SEND_DELAY_SECONDS)
    return True


async def process_due_reminders(bot: Bot, now: datetime | None = None) -> int:
    """One scheduler tick. Returns the number of reminders sent."""
    now = now or datetime.now(UTC)
    sent = 0
    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(
                or_(
                    User.reminder_evening_time.is_not(None),
                    User.reminder_morning_on.is_(True),
                    User.reminder_pattern_on.is_(True),
                )
            )
        )
        users = list(result.scalars())
        if not users:
            return 0
        open_rows = await session.execute(
            select(SleepSession).where(
                SleepSession.ended_at.is_(None), SleepSession.user_id.in_([u.id for u in users])
            )
        )
        open_by_user = {row.user_id: row for row in open_rows.scalars()}
        patterns = defaultdict(list)
        pattern_ids = [u.id for u in users if u.reminder_pattern_on]
        if pattern_ids:
            rows = await session.scalars(
                select(SleepSession)
                .where(
                    SleepSession.user_id.in_(pattern_ids),
                    SleepSession.ended_at.is_not(None),
                    SleepSession.is_nap.is_(False),
                    SleepSession.duration_minutes > 0,
                    SleepSession.ended_at >= now - timedelta(days=31),
                    SleepSession.ended_at <= now,
                )
                .order_by(SleepSession.ended_at, SleepSession.id)
            )
            for row in rows:
                patterns[row.user_id].append(_to_night(row))

        for user in users:
            try:
                open_session = open_by_user.get(user.id)
                reminder_time = user.reminder_evening_time
                catchup = reminders.EVENING_CATCHUP
                if user.reminder_pattern_on:
                    pattern = bedtime_pattern(
                        patterns[user.id], local_date_of(now, user.timezone), user.timezone, True
                    )
                    if pattern.time:
                        reminder_time = time.fromisoformat(pattern.time)
                        catchup = timedelta(minutes=15)
                day = reminders.evening_reminder_day(
                    now,
                    user.timezone,
                    reminder_time,
                    user.last_evening_reminder_date,
                    open_session is not None,
                    catchup=catchup,
                )
                if day is not None:
                    if await _claim_evening(session, user.id, day):
                        sent += await _deliver(session, bot, user, "evening")
                    continue
                if open_session is not None and reminders.morning_nudge_due(
                    now,
                    user.timezone,
                    user.reminder_morning_on,
                    open_session.started_at,
                    user.last_morning_reminder_at,
                ):
                    if await _claim_morning(session, user.id, open_session.started_at, now):
                        sent += await _deliver(session, bot, user, "morning")
            except Exception:  # one broken user must not stop the others
                logger.exception("Reminder failed for user %s", user.id)
    return sent


async def run_reminder_loop(bot: Bot, interval_seconds: int = TICK_SECONDS) -> None:
    logger.info("Reminder loop started")
    while True:
        try:
            await process_due_reminders(bot)
        except Exception:
            logger.exception("Reminder tick failed")
        await asyncio.sleep(interval_seconds)
