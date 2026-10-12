"""Pure decision logic for bot reminders (no I/O), so it can be unit-tested.

Evening reminder: sent once per local day, at the user's chosen time, unless a sleep session is
already running. If the server was down at that moment, it is still sent within a short catch-up
window, but never hours late.

Morning nudge: sent (silently) at most once per sleep session, only while a session is still open
after a plausible night (>= 5 h and <= 14 h old) and only during local morning hours.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.analytics.sleep_rules import FORGOTTEN_STOP_AFTER

EVENING_CATCHUP = timedelta(minutes=90)
MORNING_WINDOW_START = time(7, 0)
MORNING_WINDOW_END = time(12, 0)
MORNING_MIN_AGE = timedelta(hours=5)
MORNING_MAX_AGE = FORGOTTEN_STOP_AFTER  # older sessions need a wake-up time confirmed in the app


def evening_reminder_day(
    now: datetime,
    tz_name: str,
    reminder_time: time | None,
    last_sent_date: date | None,
    has_open_session: bool,
    catchup: timedelta = EVENING_CATCHUP,
) -> date | None:
    """Local date to mark as "sent" if the evening reminder is due now, else None.

    The reminder of a day stays valid across midnight (23:30 reminder + 90 min catch-up), so both
    today's and yesterday's schedule are checked; the returned day is the schedule's own date.
    """
    if reminder_time is None or has_open_session:
        return None
    tz = ZoneInfo(tz_name)
    today = now.astimezone(tz).date()
    for day in (today, today - timedelta(days=1)):
        scheduled = datetime.combine(day, reminder_time, tzinfo=tz).astimezone(UTC)
        if scheduled <= now < scheduled + catchup:
            return None if last_sent_date == day else day
    return None


def morning_nudge_due(
    now: datetime,
    tz_name: str,
    enabled: bool,
    session_started_at: datetime | None,
    last_nudge_at: datetime | None,
) -> bool:
    """True if a still-open session should get its (single) morning nudge now."""
    if not enabled or session_started_at is None:
        return False
    if not (MORNING_MIN_AGE <= now - session_started_at <= MORNING_MAX_AGE):
        return False
    local_time = now.astimezone(ZoneInfo(tz_name)).time()
    if not (MORNING_WINDOW_START <= local_time < MORNING_WINDOW_END):
        return False
    return last_nudge_at is None or last_nudge_at < session_started_at
