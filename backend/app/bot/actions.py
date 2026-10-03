"""Sleep actions triggered from the bot (buttons and /sleep, /wake). No aiogram types here."""

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.bot import texts
from app.core.db import SessionLocal
from app.services import sleep_service, user_service
from app.services.errors import DomainError

CB_START = "sleep:start"
CB_STOP = "sleep:stop"


@dataclass(frozen=True)
class Outcome:
    text: str
    language: str
    open_app: bool = False  # show an "Open SleepGuide" button (wake-up time must be confirmed)


def _local_time(moment, tz_name: str) -> str:
    return moment.astimezone(ZoneInfo(tz_name)).strftime("%H:%M")


async def start_sleep(telegram_user_id: int, language_code: str | None) -> Outcome:
    async with SessionLocal() as session:
        user = await user_service.get_or_create_by_telegram_id(session, telegram_user_id, language_code)
        already = await sleep_service.get_open_session(session, user.id) is not None
        sleep = await sleep_service.start_sleep(session, user, source="bot")
        key = "already" if already else "started"
        message = texts.text(user.language, key, time=_local_time(sleep.started_at, user.timezone))
        return Outcome(text=message, language=user.language)


async def stop_sleep(telegram_user_id: int, language_code: str | None) -> Outcome:
    async with SessionLocal() as session:
        user = await user_service.get_or_create_by_telegram_id(session, telegram_user_id, language_code)
        lang = user.language
        try:
            sleep = await sleep_service.stop_sleep(session, user)
        except DomainError as exc:
            if exc.code == "no_open_session":
                return Outcome(text=texts.text(lang, "no_open"), language=lang)
            if exc.code == "wake_time_required":
                return Outcome(text=texts.text(lang, "confirm_in_app"), language=lang, open_app=True)
            raise

        duration = texts.duration(lang, sleep.duration_minutes or 0)
        if sleep.is_nap:
            return Outcome(text=texts.text(lang, "nap", duration=duration), language=lang)

        score = await sleep_service.score_for_date(session, user, sleep.local_date)
        if score is None:
            return Outcome(text=texts.text(lang, "stopped", duration=duration), language=lang)
        message = texts.text(lang, "stopped_score", duration=duration, score=score.score)
        return Outcome(text=message, language=lang)
