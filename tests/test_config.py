import pytest
from src.config import SizingEngine


def test_get_bucket_targets_positive_net_worth():
    """Test get_bucket_targets with positive net worth values."""
    targets_1000 = SizingEngine.get_bucket_targets(1000.0)
    assert targets_1000 == {
        "equities": 333.3,
        "options": 333.3,
        "crypto": 333.3,
    }

    # 150.0 * 0.3333 = 49.995 -> rounded to 2 decimal places = 49.99
    targets_150 = SizingEngine.get_bucket_targets(150.0)
    assert targets_150 == {
        "equities": 49.99,
        "options": 49.99,
        "crypto": 49.99,
    }

    targets_10k = SizingEngine.get_bucket_targets(10000.0)
    assert targets_10k == {
        "equities": 3333.0,
        "options": 3333.0,
        "crypto": 3333.0,
    }


def test_get_bucket_targets_zero_and_negative_net_worth():
    """Test that zero or negative net worth falls back to base_val = 150.0."""
    # base_val = 150.0 -> 150.0 * 0.3333 = 49.995 -> 49.99
    expected_fallback = {
        "equities": 49.99,
        "options": 49.99,
        "crypto": 49.99,
    }

    assert SizingEngine.get_bucket_targets(0.0) == expected_fallback
    assert SizingEngine.get_bucket_targets(-100.0) == expected_fallback
    assert SizingEngine.get_bucket_targets(-0.01) == expected_fallback


def test_get_bucket_targets_structure_and_rounding():
    """Test return dictionary key structure and rounding precision."""
    net_worth = 123.456
    targets = SizingEngine.get_bucket_targets(net_worth)

    assert isinstance(targets, dict)
    assert set(targets.keys()) == {"equities", "options", "crypto"}
    for val in targets.values():
        assert isinstance(val, float)
        # Check rounded to 2 decimal places max
        assert val == round(val, 2)

    expected_val = round(123.456 * 0.3333, 2)
    assert targets["equities"] == expected_val
    assert targets["options"] == expected_val
    assert targets["crypto"] == expected_val
