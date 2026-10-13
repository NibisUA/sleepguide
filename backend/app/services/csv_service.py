"""Spreadsheet CSV import: preview first, atomic insertion, no implicit overwrites.

The date is the wake-up/end date. Local times use the account's IANA zone;
nonexistent/ambiguous DST times require explicit timestamps with UTC offsets.
"""

import csv
import io
import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import screen_time_rules, sleep_rules
from app.models import ScreenTimeDaily, SleepSession, StressLog, User, Workout
from app.schemas.csv_data import CsvImportIn, CsvPreviewOut, CsvRowOut
from app.schemas.stress import StressCreateIn
from app.schemas.workout import WorkoutCreateIn
from app.services.diary_lock import lock_diary
from app.services.errors import DomainError
from app.services.sleep_service import _validate_completed
from app.services.workout_service import _validate_completed as validate_workout

MODELS = {"sleep": SleepSession, "workout": Workout, "stress": StressLog, "screen": ScreenTimeDaily}
ALIASES = {
    "date": ["date", "дата"],
    "start": [
        "bedtime",
        "sleep_start",
        "start",
        "час коли заснув",
        "час коли ліг спати",
        "коли ліг спати",
        "час засинання",
        "початок",
    ],
    "end": ["wake_time", "wakeup", "end", "час коли прокинувся", "час пробудження", "кінець"],
    "started_at": ["started_at"],
    "ended_at": ["ended_at"],
    "type": ["type", "тип"],
    "intensity": ["intensity", "інтенсивність"],
    "time": ["time", "час"],
    "logged_at": ["logged_at"],
    "level": ["level", "рівень"],
    "category": ["category", "категорія"],
    "total_minutes": ["total_minutes", "всього хвилин"],
    "before_bed_minutes": ["before_bed_minutes", "перед сном хвилин"],
    "social_minutes": ["social_minutes", "social", "соцмережі хвилин"],
    "entertainment_minutes": ["entertainment_minutes", "entertainment", "розваги хвилин"],
    "games_minutes": ["games_minutes", "games", "ігри хвилин"],
}
HEADERS = {alias: key for key, aliases in ALIASES.items() for alias in aliases}


def parse_date(value: str) -> date:
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValueError("csv_date")


def parse_time(value: str) -> time:
    if not re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", value):
        raise ValueError("csv_time")
    try:
        return time.fromisoformat(value.zfill(5) if len(value) == 4 else value)
    except ValueError:
        raise ValueError("csv_time") from None


def local_stamp(day: date, clock: time, tz: ZoneInfo) -> datetime:
    naive = datetime.combine(day, clock)
    candidates = {
        stamp.astimezone(UTC)
        for fold in (0, 1)
        if (stamp := naive.replace(tzinfo=tz, fold=fold))
        .astimezone(UTC)
        .astimezone(tz)
        .replace(tzinfo=None)
        == naive
    }
    if len(candidates) != 1:
        raise ValueError("csv_dst")
    return candidates.pop()


def offset_stamp(value: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("csv_time") from None
    if stamp.tzinfo is None:
        raise ValueError("csv_dst")
    return stamp.astimezone(UTC)


def parse_rows(text: str, kind: str) -> list[tuple[int, dict[str, str]]]:
    text = text.lstrip("\ufeff")
    try:
        # Semicolon and tabs are common exports from localized spreadsheets.
        delimiter = max((",", ";", "\t"), key=lambda char: text.splitlines()[0].count(char))
        reader = csv.reader(io.StringIO(text), delimiter=delimiter, strict=True)
        headers = next(reader)
        normalized = [HEADERS.get(" ".join(h.strip().lower().split()), "") for h in headers]
        known = [h for h in normalized if h]
        if len(known) != len(set(known)):
            raise DomainError("csv_headers", "Duplicate column names")
        required = (
            {"date", "start", "end"}
            if kind in ("sleep", "workout")
            else ({"date", "time", "level"} if kind == "stress" else {"date", "total_minutes"})
        )
        if kind in ("sleep", "workout") and {"started_at", "ended_at"} <= set(known):
            required = set()
        if kind == "stress" and "logged_at" in known:
            required = {"level"}
        if not required <= set(known):
            raise DomainError("csv_headers", "Required columns are missing")
        rows = []
        for values in reader:
            if not any(v.strip() for v in values):
                continue
            if len(rows) >= 2000:
                raise DomainError("csv_limit", "Import at most 2000 rows at a time")
            if len(values) != len(headers):
                raise DomainError("csv_shape", f"Invalid column count on line {reader.line_num}")
            rows.append((reader.line_num, {k: v.strip() for k, v in zip(normalized, values) if k}))
        if not rows:
            raise DomainError("csv_empty", "No data rows")
        return rows
    except (csv.Error, StopIteration, IndexError):
        raise DomainError("csv_shape", "Invalid CSV") from None


def make_values(row: dict[str, str], kind: str, timezone: str, now: datetime) -> dict:
    tz = ZoneInfo(timezone)
    if kind in ("sleep", "workout"):
        if row.get("started_at") and row.get("ended_at"):
            start, end = offset_stamp(row["started_at"]), offset_stamp(row["ended_at"])
            # Export retains exact UTC offsets/microseconds for lossless roundtrips.
            # Never silently ignore a user's edits to the visible spreadsheet columns.
            if (
                (row.get("date") and parse_date(row["date"]) != end.astimezone(tz).date())
                or (
                    row.get("start")
                    and parse_time(row["start"])
                    != start.astimezone(tz).time().replace(microsecond=0)
                )
                or (
                    row.get("end")
                    and parse_time(row["end"]) != end.astimezone(tz).time().replace(microsecond=0)
                )
            ):
                raise ValueError("csv_timestamp_mismatch")
        else:
            day, start_time, end_time = (
                parse_date(row["date"]),
                parse_time(row["start"]),
                parse_time(row["end"]),
            )
            start_day = day - timedelta(days=1) if start_time > end_time else day
            start, end = local_stamp(start_day, start_time, tz), local_stamp(day, end_time, tz)
        if kind == "sleep":
            _validate_completed(start, end, now)
            minutes = sleep_rules.duration_minutes(start, end)
            return dict(
                started_at=start,
                ended_at=end,
                duration_minutes=minutes,
                local_date=end.astimezone(tz).date(),
                is_nap=sleep_rules.is_nap(minutes),
                source="csv",
            )
        body = WorkoutCreateIn(
            started_at=start,
            ended_at=end,
            type=row.get("type") or "other",
            intensity=row.get("intensity") or "moderate",
        )
        validate_workout(start, end, now)
        minutes = sleep_rules.duration_minutes(start, end)
        return dict(
            started_at=start,
            ended_at=end,
            duration_minutes=minutes,
            local_date=start.astimezone(tz).date(),
            type=body.type,
            intensity=body.intensity,
            source="csv",
        )
    if kind == "stress":
        stamp = (
            offset_stamp(row["logged_at"])
            if row.get("logged_at")
            else local_stamp(parse_date(row["date"]), parse_time(row["time"]), tz)
        )
        if stamp > now + sleep_rules.MAX_FUTURE_SKEW:
            raise ValueError("invalid_time")
        if row.get("logged_at") and (
            (row.get("date") and parse_date(row["date"]) != stamp.astimezone(tz).date())
            or (
                row.get("time")
                and parse_time(row["time"]) != stamp.astimezone(tz).time().replace(microsecond=0)
            )
        ):
            raise ValueError("csv_timestamp_mismatch")
        body = StressCreateIn(
            logged_at=stamp, level=int(row["level"]), category=row.get("category") or None
        )
        return dict(
            logged_at=stamp,
            local_date=stamp.astimezone(tz).date(),
            level=body.level,
            category=body.category,
        )
    day = parse_date(row["date"])
    total = int(row["total_minutes"])
    before = int(row["before_bed_minutes"]) if row.get("before_bed_minutes") else None
    if (
        day > now.astimezone(tz).date()
        or not 0 <= total <= 1440
        or (before is not None and not 0 <= before <= min(120, total))
    ):
        raise ValueError("csv_screen")
    categories = {
        key: int(row[key]) if row[key] else None
        for key in screen_time_rules.SCREEN_CATEGORIES
        if key in row
    }
    if not screen_time_rules.valid_categories(total, categories):
        raise ValueError("invalid_screen_categories")
    return dict(
        local_date=day, total_minutes=total, before_bed_minutes=before, source="csv", **categories
    )


def identity(values: dict, kind: str, category_keys: tuple[str, ...] = ()) -> tuple:
    keys = {
        "sleep": ("started_at", "ended_at"),
        "workout": ("started_at", "ended_at", "type", "intensity"),
        "stress": ("logged_at", "level", "category"),
        "screen": ("local_date", "total_minutes", "before_bed_minutes"),
    }[kind]
    if kind == "screen":
        keys += category_keys
    return tuple(values[k] for k in keys)


def conflicts(a: dict, b: dict, kind: str) -> bool:
    if kind == "screen":
        return a["local_date"] == b["local_date"]
    if kind in ("sleep", "workout"):
        return (
            a["started_at"] < (b["ended_at"] or datetime.max.replace(tzinfo=UTC))
            and b["started_at"] < a["ended_at"]
        )
    return False


async def import_csv(
    session: AsyncSession, user: User, body: CsvImportIn, *, commit: bool = False
) -> CsvPreviewOut:
    if commit:
        await lock_diary(session, user.id)
    rows = parse_rows(body.csv, body.kind)
    model = MODELS[body.kind]
    existing = [
        dict((column.name, getattr(row, column.name)) for column in model.__table__.columns)
        for row in await session.scalars(select(model).where(model.user_id == user.id))
    ]
    category_keys = (
        tuple(key for key in screen_time_rules.SCREEN_CATEGORIES if key in rows[0][1])
        if body.kind == "screen"
        else ()
    )
    seen = {identity(row, body.kind, category_keys) for row in existing}
    valid, results = [], []
    now = datetime.now(UTC)
    for line, raw in rows:
        out = CsvRowOut(line=line, date=raw.get("date", ""), status="ready")
        try:
            values = make_values(raw, body.kind, user.timezone, now)
            out.date = values["local_date"].isoformat()
            if body.kind == "screen":
                out.categories = {key: values[key] for key in category_keys} or None
            out.summary = (
                f"{values['started_at'].astimezone(ZoneInfo(user.timezone)):%H:%M} → "
                f"{values['ended_at'].astimezone(ZoneInfo(user.timezone)):%H:%M} · {values['duration_minutes']} min"
                if body.kind in ("sleep", "workout")
                else str(values.get("level", values.get("total_minutes")))
            )
            key = identity(values, body.kind, category_keys)
            if key in seen:
                out.status, out.code = "duplicate", "csv_duplicate"
            elif any(conflicts(values, old, body.kind) for old in existing + valid):
                out.status, out.code = "error", "csv_conflict"
            else:
                valid.append(values)
                seen.add(key)
        except (ValueError, KeyError, DomainError) as exc:
            out.status = "error"
            out.code = exc.code if isinstance(exc, DomainError) else str(exc)
            if out.code not in {
                "csv_timestamp_mismatch",
                "csv_date",
                "csv_time",
                "csv_dst",
                "csv_screen",
                "invalid_screen_categories",
                "invalid_time",
                "too_long",
            }:
                out.code = "csv_value"
        results.append(out)
    errors = sum(row.status == "error" for row in results)
    if commit and errors:
        raise DomainError("csv_invalid", "Correct all errors before importing")
    if commit:
        session.add_all(model(user_id=user.id, **values) for values in valid)
        await session.commit()
    return CsvPreviewOut(
        rows=results,
        ready=len(valid),
        duplicates=sum(row.status == "duplicate" for row in results),
        errors=errors,
        imported=len(valid) if commit else 0,
        timezone=user.timezone,
    )


async def export_csv(session: AsyncSession, user: User, kind: str) -> str:
    model, tz = MODELS[kind], ZoneInfo(user.timezone)
    rows = await session.scalars(select(model).where(model.user_id == user.id).order_by(model.id))
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if kind in ("sleep", "workout"):
        writer.writerow(
            [
                "Дата",
                "Час коли заснув" if kind == "sleep" else "Початок",
                "Час коли прокинувся" if kind == "sleep" else "Кінець",
                "Кількість годин сну" if kind == "sleep" else "Тривалість",
                "started_at",
                "ended_at",
            ]
            + (["type", "intensity"] if kind == "workout" else [])
        )
        for row in rows:
            if row.ended_at is None:
                continue
            writer.writerow(
                [
                    row.ended_at.astimezone(tz).strftime("%d.%m.%Y"),
                    row.started_at.astimezone(tz).strftime("%H:%M:%S"),
                    row.ended_at.astimezone(tz).strftime("%H:%M:%S"),
                    f"{row.duration_minutes // 60}:{row.duration_minutes % 60:02d}",
                    row.started_at.isoformat(),
                    row.ended_at.isoformat(),
                ]
                + ([row.type, row.intensity] if kind == "workout" else [])
            )
    elif kind == "stress":
        writer.writerow(["Дата", "Час", "level", "category", "logged_at"])
        for row in rows:
            writer.writerow(
                [
                    row.logged_at.astimezone(tz).strftime("%d.%m.%Y"),
                    row.logged_at.astimezone(tz).strftime("%H:%M:%S"),
                    row.level,
                    row.category or "",
                    row.logged_at.isoformat(),
                ]
            )
    else:
        writer.writerow(
            ["Дата", "total_minutes", "before_bed_minutes", *screen_time_rules.SCREEN_CATEGORIES]
        )
        for row in rows:
            writer.writerow(
                [
                    row.local_date.strftime("%d.%m.%Y"),
                    row.total_minutes,
                    row.before_bed_minutes if row.before_bed_minutes is not None else "",
                    *(
                        getattr(row, key) if getattr(row, key) is not None else ""
                        for key in screen_time_rules.SCREEN_CATEGORIES
                    ),
                ]
            )
    return "\ufeff" + output.getvalue()
