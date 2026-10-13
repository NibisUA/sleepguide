"""Pure Screen Time rules (no I/O)."""

from datetime import date, timedelta

MAX_TOTAL_MINUTES = 24 * 60
MAX_BEFORE_BED_MINUTES = 120  # "phone use in the ~2 hours before going to bed"
MAX_DAYS_BACK = 365
SCREEN_CATEGORIES = ("social_minutes", "entertainment_minutes", "games_minutes")


def valid_categories(total_minutes: int, categories: dict[str, int | None]) -> bool:
    known = [value for value in categories.values() if value is not None]
    return (
        all(type(value) is int and 0 <= value <= 1440 for value in known)
        and sum(known) <= total_minutes
    )


def is_valid_usage(total_minutes: int, before_bed_minutes: int | None) -> bool:
    """Total within one day; pre-bed usage (optional) within 2 h and never above the total."""
    if not 0 <= total_minutes <= MAX_TOTAL_MINUTES:
        return False
    if before_bed_minutes is None:
        return True
    return 0 <= before_bed_minutes <= min(total_minutes, MAX_BEFORE_BED_MINUTES)


def is_date_in_range(day: date, today: date) -> bool:
    """A day can be logged from a year ago up to today (never the future)."""
    return today - timedelta(days=MAX_DAYS_BACK) <= day <= today
