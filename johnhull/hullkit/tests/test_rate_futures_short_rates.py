"""Hull §6.3 consistent source outputs and documented source arithmetic errors."""

import math

import numpy as np
import pytest
from hullkit import _rate_futures as f


def test_source_rate_futures_table_and_monthly_quote_amounts():
    assert f.rate_futures_quote(0.0075) == pytest.approx(99.250)
    a = f.rate_futures_cash(99.725, 99.685)
    assert [a["bp_value"], a["profit"]] == pytest.approx([25, -100])
    assert [
        f.rate_futures_cash(a, b)["profit"]
        for a, b in [(99.720, 99.715), (99.715, 99.665), (99.800, 99.810)]
    ] == pytest.approx([-12.5, -125, 25])
    assert f.rate_futures_cash(99.720, 99.810)["profit"] == pytest.approx(225)
    interest = 1e6 * 0.0019 * 0.25
    assert [interest, interest + 225, 1e6 / (1 + 0.0028 * 0.25)] == pytest.approx(
        [475, 700, 999300], abs=0.5
    )
    assert [
        100 - f.rate_futures_quote(0.000475),
        100 - f.rate_futures_quote(0.00055),
    ] == pytest.approx([0.0475, 0.055])
    assert f.rate_futures_cash(99, 99, notional=5e6, accrual=1 / 12)["bp_value"] == pytest.approx(
        41.67, abs=0.005
    )


def test_source_borrow_hedge_scenarios_and_zero_extensions():
    up = f.rate_futures_borrow_hedge(1e8, 0.02, 0.25, 99.99, 99.2, contracts=100)
    down = f.rate_futures_borrow_hedge(1e8, 0.02, 0.25, 99.99, 100.4, contracts=100)
    assert [
        up["change_bp"],
        up["futures_profit"],
        up["interest_cash"],
        up["net_interest"],
    ] == pytest.approx([79, 197500, 700000, 502500])
    assert [
        -down["change_bp"],
        -down["futures_profit"],
        down["interest_cash"],
        down["net_interest"],
    ] == pytest.approx([41, 102500, 400000, 502500])
    first = f.extend_zero(300, 0.028, 0.033, 391)
    second = f.extend_zero(391, first, 0.035, 489)
    assert [100 * first, 100 * second] == pytest.approx([2.916, 3.033], abs=0.0005)
    assert f.remaining_zero(0.025, 3 / 12, 0.02, 1 / 12) == pytest.approx(0.0275)


def test_independent_hedge_cash_identity_discount_chain_and_observed_stub():
    for quote in [97, 99.2, 100.4, 102]:
        a = f.rate_futures_borrow_hedge(1e8, 0.02, 0.25, 99.99, quote, contracts=100)
        expected = 1e8 * 0.25 * (0.02 + (100 - 99.99) / 100)
        assert a["net_interest"] == pytest.approx(expected, abs=1e-7)
    p1 = math.exp(-0.028 * 300 / 365)
    p2 = p1 * math.exp(-0.033 * 91 / 365)
    assert f.extend_zero(300, 0.028, 0.033, 391) == pytest.approx(-math.log(p2) / (391 / 365))
    whole = math.exp(0.025 * 3 / 12)
    known = math.exp(0.02 * 1 / 12)
    assert f.remaining_zero(0.025, 0.25, 0.02, 1 / 12) == pytest.approx(
        math.log(whole / known) / (2 / 12)
    )
    assert f.adjust_forward_rate(0.03, 0.001) == pytest.approx(0.029)


def test_independent_daily_sofr_window_excludes_end_and_carries_weekend():
    fixings = {"2020-06-18": 0.01, "2020-06-19": 0.02, "2020-06-22": 0.03, "2020-06-23": 9.0}
    a = f.sofr_fixing_window("2020-06-18", "2020-06-23", fixings)
    daily = np.array([0.01, 0.02, 0.02, 0.02, 0.03])
    assert a["arithmetic"] == pytest.approx((0.01 + 3 * 0.02 + 0.03) / 5)
    capital = 1.0
    for rate in daily:
        capital += capital * rate / 360
    assert a["growth"] == pytest.approx(capital, abs=1e-14)
    assert a["compounded"] == pytest.approx((capital - 1) * 360 / 5)
    assert a["daily_rates"] == pytest.approx(daily)
