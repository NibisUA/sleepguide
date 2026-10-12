from datetime import date, timedelta


def count_streaks(dates: set[date], today: date) -> dict:
    """Stored local dates, one credit/day; today may still be awaiting a log."""
    days = sorted(day for day in dates if day <= today)
    longest = run = 0
    previous = None
    for day in days:
        run = run + 1 if previous == day - timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    last = days[-1] if days else None
    current = run if last in (today, today - timedelta(days=1)) else 0
    return dict(
        current=current,
        longest=longest,
        total_days=len(days),
        last_date=last,
        counted_today=today in dates,
    )
