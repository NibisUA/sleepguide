from app.analytics import stress_rules as s


def test_day_average_has_one_decimal_and_handles_empty_days():
    assert s.day_average([]) is None
    assert s.day_average([3]) == 3.0
    assert s.day_average([2, 4]) == 3.0
    assert s.day_average([4, 4, 5]) == 4.3  # 13 / 3
    assert s.day_average([2, 3, 3]) == 2.7  # 8 / 3


def test_day_max():
    assert s.day_max([]) is None
    assert s.day_max([2, 5, 3]) == 5


def test_high_stress_day_starts_at_level_four():
    assert not s.is_high_stress_day([])
    assert not s.is_high_stress_day([1, 2, 3, 3])
    assert s.is_high_stress_day([1, 4])
    assert s.is_high_stress_day([5])


def test_categories_are_a_fixed_set():
    assert s.STRESS_CATEGORIES == (
        "university",
        "work",
        "relationships",
        "money",
        "sleep",
        "training",
        "personal",
        "other",
    )
    assert (s.MIN_LEVEL, s.MAX_LEVEL) == (1, 5)
