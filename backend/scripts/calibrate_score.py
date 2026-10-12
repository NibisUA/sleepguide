"""Evaluate a private schema 1.2 export locally; no network or database access."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analytics.calibration import KEYS, evaluate_candidates  # noqa: E402
from app.analytics.sleep_score import Night  # noqa: E402
from app.schemas.privacy import DataExportOut  # noqa: E402
from app.services.personal_service import score_snapshot  # noqa: E402


def audit_export(data, kind):
    nights = sorted(
        [
            Night(row.started_at, row.ended_at, row.duration_minutes, row.local_date)
            for row in data.sleep_sessions
            if not row.is_nap and row.ended_at and row.duration_minutes and row.local_date
        ],
        key=lambda n: (n.local_date, n.started_at),
    )
    rows, stale, limited = [], 0, 0
    for feedback in data.sleep_feedback:
        score, signature = score_snapshot(feedback.local_date, nights, data.user)
        if (
            score is None
            or signature != feedback.context_signature
            or feedback.algorithm_version != "1.0"
        ):
            stale += 1
        elif feedback.limited_data or any(key not in feedback.components for key in KEYS):
            limited += 1
        else:
            rows.append(
                {
                    "date": feedback.local_date.isoformat(),
                    "rating": feedback.rating,
                    "components": feedback.components,
                }
            )
    return {
        **evaluate_candidates(rows, kind),
        "excluded_stale": stale,
        "excluded_limited": limited,
        "export_schema": data.schema_version,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", dest="source", type=Path, required=True)
    parser.add_argument(
        "--data-kind",
        choices=("real", "synthetic"),
        required=True,
        help="Explicit provenance declaration; synthetic checks cannot support calibration",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must differ from the source export")
    data = DataExportOut.model_validate_json(args.source.read_text(encoding="utf-8"))
    report = audit_export(data, args.data_kind)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{report['status']}: {report['eligible_nights']} eligible nights; weights unchanged")


if __name__ == "__main__":
    main()
