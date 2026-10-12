"""Pure workout rules (no I/O)."""

from datetime import timedelta

WORKOUT_TYPES = ("gym", "home", "running", "football", "walking", "other")
WORKOUT_INTENSITIES = ("easy", "moderate", "hard", "very_hard")

DEFAULT_TYPE = "gym"
DEFAULT_INTENSITY = "moderate"

# A workout longer than this is almost certainly a forgotten Stop: stopping "now" then requires an
# explicit end time, and no workout (running or retroactive) may exceed it.
MAX_WORKOUT = timedelta(hours=6)


def needs_end_time(started_at, now) -> bool:
    """True when a running workout is old enough that "finish now" would be a forgotten Stop."""
    return now - started_at > MAX_WORKOUT


def is_too_long(started_at, ended_at) -> bool:
    return ended_at - started_at > MAX_WORKOUT
