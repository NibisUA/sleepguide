"""Offline candidate evaluation. Never changes the production formula."""

from statistics import pstdev

from app.analytics.personal import spearman

KEYS = ("duration", "consistency", "sleep_debt", "bedtime_timing")
CURRENT = (40, 30, 20, 10)


def weighted_score(row, weights):
    return round(sum(row["components"][key] * weight for key, weight in zip(KEYS, weights)))


def evaluate_candidates(rows, data_kind):
    ordered = sorted(rows, key=lambda r: r["date"])
    report = {
        "algorithm_version": "1.0",
        "data_kind": data_kind,
        "eligible_nights": len(rows),
        "minimum_nights": 60,
        "weights_applied": False,
        "current_weights": dict(zip(KEYS, CURRENT)),
    }
    if len(rows) < 60:
        return {**report, "status": "insufficient_data"}
    split = min(int(len(rows) * 0.7), len(rows) - 20)
    train, holdout = ordered[:split], ordered[split:]
    report.update(
        train_nights=len(train),
        holdout_nights=len(holdout),
        train_to=train[-1]["date"],
        holdout_from=holdout[0]["date"],
    )
    if any(
        len({r["rating"] for r in group}) < 3
        or pstdev([weighted_score(r, CURRENT) for r in group]) < 5
        for group in (train, holdout)
    ):
        return {**report, "status": "insufficient_variation"}

    def association(group, weights):
        return spearman(
            [weighted_score(row, weights) for row in group], [row["rating"] for row in group]
        )

    candidates = []
    for duration in range(20, 61, 5):
        for consistency in range(10, 51, 5):
            for debt in range(5, 36, 5):
                bedtime = 100 - duration - consistency - debt
                if 0 <= bedtime <= 20:
                    weights = (duration, consistency, debt, bedtime)
                    rho = association(train, weights)
                    if rho is not None:
                        candidates.append(
                            (rho, -sum(abs(a - b) for a, b in zip(weights, CURRENT)), weights)
                        )
    if not candidates:
        return {**report, "status": "insufficient_variation"}
    _, _, best = max(candidates)
    current_holdout = association(holdout, CURRENT)
    candidate_holdout = association(holdout, best)
    improvement = (
        round(candidate_holdout - current_holdout, 3)
        if current_holdout is not None and candidate_holdout is not None
        else None
    )
    supported = improvement is not None and improvement >= 0.1 and best != CURRENT
    return {
        **report,
        "status": "synthetic_fixture_only"
        if data_kind == "synthetic"
        else "manual_review_required",
        "candidates_tested": len(candidates),
        "candidate_weights": dict(zip(KEYS, best)),
        "current_train_rho": association(train, CURRENT),
        "candidate_train_rho": association(train, best),
        "current_holdout_rho": current_holdout,
        "candidate_holdout_rho": candidate_holdout,
        "holdout_improvement": improvement,
        "candidate_supported": supported and data_kind == "real",
        "limitations": [
            "Temporal holdout within one person; not population validation.",
            "Self-reported restedness is ordinal, not a medical outcome.",
            "Keep v1.0 until independent real-data review and versioned release.",
        ],
    }
