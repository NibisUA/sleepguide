"""Pure stress rules (no I/O)."""

from collections.abc import Sequence

STRESS_CATEGORIES = (
    "university",
    "work",
    "relationships",
    "money",
    "sleep",
    "training",
    "personal",
    "other",
)
MIN_LEVEL = 1
MAX_LEVEL = 5

# A day with at least one rating >= this counts as a "high-stress day" (used by insights later).
HIGH_STRESS_LEVEL = 4


def day_average(levels: Sequence[int]) -> float | None:
    """Average rating of the day, one decimal (None without ratings)."""
    return round(sum(levels) / len(levels), 1) if levels else None


def day_max(levels: Sequence[int]) -> int | None:
    return max(levels) if levels else None


def is_high_stress_day(levels: Sequence[int]) -> bool:
    return any(level >= HIGH_STRESS_LEVEL for level in levels)
