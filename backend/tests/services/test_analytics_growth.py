from decimal import Decimal

from app.services.analytics_rules import calculate_period_growth


def test_positive_growth():
    # 100 -> 125 (+25.00%)
    res = calculate_period_growth(Decimal("125.00"), Decimal("100.00"))
    assert res == Decimal("25.00")

    # integers
    res_int = calculate_period_growth(200, 100)
    assert res_int == Decimal("100.00")


def test_negative_growth():
    # 100 -> 75 (-25.00%)
    res = calculate_period_growth(Decimal("75.00"), Decimal("100.00"))
    assert res == Decimal("-25.00")

    # 1000 -> 215 (-78.50%)
    res_orders = calculate_period_growth(215, 1000)
    assert res_orders == Decimal("-78.50")


def test_current_zero_previous_positive():
    # 50 -> 0 (-100.00%)
    res = calculate_period_growth(0, 50)
    assert res == Decimal("-100.00")

    res_dec = calculate_period_growth(Decimal("0.0"), Decimal("1234.56"))
    assert res_dec == Decimal("-100.00")


def test_previous_zero_current_positive():
    # 0 -> 100 (baseline is zero, do not fabricate infinite percentage)
    res = calculate_period_growth(100, 0)
    assert res is None

    res_dec = calculate_period_growth(Decimal("500.0"), Decimal("0.0"))
    assert res is None


def test_both_zero():
    # 0 -> 0 (no activity, baseline is zero)
    res = calculate_period_growth(0, 0)
    assert res is None

    res_dec = calculate_period_growth(Decimal("0.0"), Decimal("0.0"))
    assert res is None


def test_none_inputs():
    assert calculate_period_growth(None, 100) is None
    assert calculate_period_growth(100, None) is None
    assert calculate_period_growth(None, None) is None

