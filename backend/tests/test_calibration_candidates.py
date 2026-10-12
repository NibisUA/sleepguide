from app.analytics.calibration import CURRENT, KEYS, evaluate_candidates


def sample(count=90, constant=False):
    rows = []
    for i in range(count):
        value = (i * 13 % 31) / 30
        rows.append(
            {
                "date": f"{i:04}",
                "rating": 3 if constant else min(5, 1 + int(value * 5)),
                "components": dict(zip(KEYS, (value, 0.5, value, 0.7))),
            }
        )
    return rows


def test_minimum_holdout_variation_and_no_synthetic_validation():
    assert evaluate_candidates(sample(59), "real")["status"] == "insufficient_data"
    assert evaluate_candidates(sample(constant=True), "real")["status"] == "insufficient_variation"
    result = evaluate_candidates(sample(), "synthetic")
    assert result["status"] == "synthetic_fixture_only" and not result["candidate_supported"]
    assert not result["weights_applied"] and result["holdout_nights"] >= 20
    assert result["train_to"] < result["holdout_from"]
    assert sum(result["candidate_weights"].values()) == 100


def test_evaluation_does_not_fit_against_holdout():
    rows = sample()
    original = evaluate_candidates(rows, "real")
    for row in rows[63:]:
        row["rating"] = 6 - row["rating"]
    changed = evaluate_candidates(rows, "real")
    assert original["candidate_weights"] == changed["candidate_weights"]
    assert changed["candidate_holdout_rho"] < 0 and not changed["candidate_supported"]
    assert changed["current_weights"] == dict(zip(KEYS, CURRENT)) and not changed["weights_applied"]
