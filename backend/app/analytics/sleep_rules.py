"""Pure sleep-session rules (no I/O), easy to unit-test."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

NAP_MAX_MINUTES = 180
FORGOTTEN_STOP_AFTER = timedelta(hours=14)
MAX_FUTURE_SKEW = timedelta(minutes=5)


def local_date_of(moment: datetime, tz_name: str) -> date:
    """Local calendar date (in the user's time zone) of an aware datetime."""
    return moment.astimezone(ZoneInfo(tz_name)).date()


def duration_minutes(started_at: datetime, ended_at: datetime) -> int:
    return int((ended_at - started_at).total_seconds() // 60)


def is_nap(minutes: int) -> bool:
    return minutes < NAP_MAX_MINUTES


def needs_wake_confirmation(started_at: datetime, now: datetime) -> bool:
    """True when a session has been open so long that "Stop now" is probably a forgotten Stop."""
    return now - started_at > FORGOTTEN_STOP_AFTER


def is_valid_end(started_at: datetime, ended_at: datetime, now: datetime) -> bool:
    return started_at < ended_at <= now + MAX_FUTURE_SKEW
