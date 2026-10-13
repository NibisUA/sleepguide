from datetime import UTC, datetime

import pytest

from app.services.csv_service import local_stamp, make_values, parse_date, parse_rows, parse_time
from app.services.errors import DomainError

NOW = datetime(2026, 10, 13, 12, tzinfo=UTC)


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
def test_ukrainian_spreadsheet_and_delimiters(delimiter):
    text = (
        "\ufeff"
        + delimiter.join(["Дата", "Час коли заснув", "Час коли прокинувся", "Кількість годин сну"])
        + "\n"
        + delimiter.join(["26.09.2026", "0:00", "8:00", "8:00"])
    )
    rows = parse_rows(text, "sleep")
    values = make_values(rows[0][1], "sleep", "Europe/Kyiv", NOW)
    assert rows[0][0] == 2 and values["duration_minutes"] == 480
    assert values["local_date"].isoformat() == "2026-09-26"


def test_overnight_and_seconds_and_nap_classification():
    row = dict(date="2026-09-26", start="23:30:15", end="07:30:45")
    result = make_values(row, "sleep", "Europe/Kyiv", NOW)
    assert result["started_at"].day == 25 and result["ended_at"].day == 26
    assert result["duration_minutes"] == 480 and not result["is_nap"]
    row.update(start="14:00", end="15:00")
    assert make_values(row, "sleep", "UTC", NOW)["is_nap"]


@pytest.mark.parametrize("day", ["2026-03-29", "2026-10-25"])
def test_dst_rejects_ambiguous_or_missing_local_time(day):
    from zoneinfo import ZoneInfo

    with pytest.raises(ValueError, match="csv_dst"):
        local_stamp(parse_date(day), parse_time("03:30"), ZoneInfo("Europe/Kyiv"))


def test_explicit_offsets_allow_a_dst_roundtrip():
    result = make_values(
        dict(started_at="2026-03-29T01:30:00+02:00", ended_at="2026-03-29T08:30:00+03:00"),
        "sleep",
        "Europe/Kyiv",
        NOW,
    )
    assert result["duration_minutes"] == 360


@pytest.mark.parametrize(
    "text,code",
    [
        ("bedtime,wake_time\n23:00,07:00", "csv_headers"),
        ("date,date,bedtime,wake_time\n2026-09-01,2026-09-01,23:00,07:00", "csv_headers"),
        ("date,bedtime,wake_time\n2026-09-01,23:00", "csv_shape"),
        ("date,bedtime,wake_time\n", "csv_empty"),
    ],
)
def test_csv_structure_errors(text, code):
    with pytest.raises(DomainError) as exc:
        parse_rows(text, "sleep")
    assert exc.value.code == code


@pytest.mark.parametrize(
    "row",
    [
        dict(date="2026-10-99", start="23:00", end="07:00"),
        dict(date="2026-09-26", start="25:00", end="07:00"),
        dict(date="2026-09-26", start="07:00", end="07:00"),
        dict(date="2030-09-26", start="23:00", end="07:00"),
    ],
)
def test_bad_sleep_values_never_become_entries(row):
    with pytest.raises((ValueError, DomainError)):
        make_values(row, "sleep", "Europe/Kyiv", NOW)


def test_workout_uses_existing_six_hour_limit():
    with pytest.raises(DomainError, match="6 hours"):
        make_values(dict(date="2026-09-26", start="08:00", end="15:00"), "workout", "UTC", NOW)


def test_row_limit():
    with pytest.raises(DomainError) as exc:
        parse_rows("date,bedtime,wake_time\n" + "2026-09-26,23:00,07:00\n" * 2001, "sleep")
    assert exc.value.code == "csv_limit"


def test_visible_csv_edits_are_not_silently_ignored_by_exact_timestamps():
    with pytest.raises(ValueError, match="csv_timestamp_mismatch"):
        make_values(
            dict(
                date="2026-09-26",
                start="22:00",
                end="07:30",
                started_at="2026-09-25T23:30:00+03:00",
                ended_at="2026-09-26T07:30:00+03:00",
            ),
            "sleep",
            "Europe/Kyiv",
            NOW,
        )
