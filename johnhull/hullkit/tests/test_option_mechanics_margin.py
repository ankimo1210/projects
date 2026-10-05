"""Hull §10.7 historical margin arithmetic; no current broker-rule claims."""

import importlib
from fractions import Fraction

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._option_mechanics")


def test_printed_example_103_call_put_and_premium_credit():
    call = model().legacy_short_option_margin(38, 40, 5, contracts=4)
    put = model().legacy_short_option_margin(38, 40, 5, contracts=4, kind="put")
    assert call["primary"] == pytest.approx(4240)
    assert call["floor"] == pytest.approx(3520)
    assert call["required"] == pytest.approx(4240)
    assert put["required"] == pytest.approx(5040)
    assert call["mark_value"] == pytest.approx(2000)
    assert call["required"] - call["mark_value"] == pytest.approx(2240)


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("risk_rate", [Fraction(1, 5), Fraction(3, 20)])
def test_independent_piecewise_analytic_margin_and_fraction_arithmetic(kind, risk_rate):
    spots = [0, 10, 20, 30, 35, 38, 40, 42, 45, 50, 80]
    strike, mark, floor_rate = Fraction(40), Fraction(5), Fraction(1, 10)
    expected = []
    for stock in map(Fraction, spots):
        if kind == "call":
            primary = mark + (risk_rate + 1) * stock - strike if stock < strike else mark + risk_rate * stock
            floor = mark + floor_rate * stock
            use_floor = stock < strike / (1 + risk_rate - floor_rate)
        else:
            primary = mark + risk_rate * stock if stock <= strike else mark + strike - (1 - risk_rate) * stock
            floor = mark + floor_rate * strike
            use_floor = stock < floor_rate * strike / risk_rate or stock > strike * (1 - floor_rate) / (1 - risk_rate)
        expected.append(float(400 * (floor if use_floor else primary)))
    actual = model().legacy_short_option_margin(
        spots, float(strike), float(mark), kind=kind, contracts=4, risk_rate=float(risk_rate)
    )
    assert np.allclose(actual["required"], expected, atol=1e-9, rtol=1e-12)


def test_original_twenty_percent_binding_thresholds():
    for kind, spot in [("call", 40 / 1.1), ("put", 20), ("put", 45)]:
        row = model().legacy_short_option_margin(spot, 40, 5, kind=kind)
        assert row["primary"] == pytest.approx(row["floor"], abs=1e-10)


@pytest.mark.parametrize("withdraw", [True, False])
def test_daily_mark_recalculation_and_cash_account_conservation(withdraw):
    row = model().legacy_margin_cashflows(
        [38, 42, 35], 40, [5, 10, 2], initial_cash=2000, contracts=4, withdraw_excess=withdraw
    )
    assert row["required"] == pytest.approx([4240, 7360, 2200])
    assert row["top_up"] == pytest.approx([2240, 3120, 0])
    assert row["withdrawal"] == pytest.approx([0, 0, 5160 if withdraw else 0])
    assert row["balance"] == pytest.approx([4240, 7360, 2200 if withdraw else 7360])
    expected_balance = 2000 + np.cumsum(row["top_up"] - row["withdrawal"])
    assert np.allclose(row["balance"], expected_balance, atol=1e-9, rtol=1e-12)
    assert np.all(row["balance"] >= row["required"] - 1e-9)


def test_covered_call_stock_borrowing_limit_against_half_exercise_value():
    limit = model().legacy_covered_call_loan_limit([30, 40, 50], 40, units=400)
    assert limit == pytest.approx([6000, 8000, 8000])
    assert limit == pytest.approx([400 * 30 / 2, 400 * 40 / 2, 400 * 40 / 2])


def test_historical_long_option_loan_limit_uses_strictly_more_than_nine_months():
    actual = model().legacy_long_option_loan_limit(10, [8, 9, 10], units=100)
    assert actual == pytest.approx([0, 0, 250])


@pytest.mark.parametrize("call", [
    lambda m: m.legacy_short_option_margin(38, 40, 5, multiplier=0),
    lambda m: m.legacy_short_option_margin(38, 40, 5, contracts=-1),
    lambda m: m.legacy_short_option_margin(38, 40, -5),
    lambda m: m.legacy_long_option_loan_limit(10, -1),
])
def test_undefined_margin_quantity_or_expiry_rejected(call):
    with pytest.raises(ValueError):
        call(model())
