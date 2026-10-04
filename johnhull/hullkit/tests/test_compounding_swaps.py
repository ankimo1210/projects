"""Compounding recurrence, printed truncation route, independent rate paths."""

import importlib
import itertools
import math
from datetime import date

import numpy as np
import pytest
from hullkit._nonstandard_legs import leg_schedule
from hullkit.rfr import BusinessCalendar


def model():
    return importlib.import_module("hullkit._compounding_swaps")


def test_example34_1_all_balances_full_precision_and_displayed_cashflow_route():
    m = model()
    fixed = m.forward_realized_leg([0.04] * 3, [0.039] * 3, [1] * 3, 100, 1 / 1.04**3)
    floating = m.forward_realized_leg([0.05] * 3, [0.048] * 3, [1] * 3, 100, 1 / 1.04**3)
    assert fixed["balances"][1:] == pytest.approx([4, 8.156, 12.474084], abs=1e-10)
    assert floating["balances"][1:] == pytest.approx([5, 10.24, 15.731520], abs=1e-10)
    assert fixed["balances"][1] * 1.039 == pytest.approx(4.156, abs=1e-12)
    assert fixed["balances"][2] * 1.039 == pytest.approx(8.474, abs=0.0005)
    assert floating["balances"][1] * 1.048 == pytest.approx(5.24, abs=1e-12)
    # Source 10.731 and 15.731 are truncations, not nearest-rounded pins.
    assert floating["balances"][2] * 1.048 - 10.731 == pytest.approx(0.00052, abs=1e-10)
    exact = floating["pv"] - fixed["pv"]
    assert exact == pytest.approx(2.8958487426035533, abs=1e-10)
    displayed = (15.731 - 12.474) / 1.04**3
    assert displayed == pytest.approx(2.895, abs=0.0005)
    assert abs(exact - 2.895) > 0.0005
    independent = (
        100 * (0.05 * ((1.048) ** 3 - 1) / 0.048 - 0.04 * ((1.039) ** 3 - 1) / 0.039) / 1.04**3
    )
    assert exact == pytest.approx(independent, abs=1e-11)


def test_bs34_2_twenty_coupon_accumulations_and_final_single_payment():
    m = model()
    start = date(2021, 1, 11)
    end = date(2026, 1, 11)
    rows = leg_schedule(start, end, 3, 365, calendar=BusinessCalendar(), adjust=False)
    ax = np.array([r["accrual"] for r in rows])
    af = ax * 365 / 360
    reference = np.expm1(0.045 * ax) / af
    discount = math.exp(-0.03 * (end - start).days / 365)
    fixed = m.forward_realized_leg(np.full(20, 0.02), np.full(20, 0.023), ax, 1e8, discount)
    floating = m.forward_realized_leg(reference + 0.002, reference, af, 1e8, discount)
    for row in [fixed, floating]:
        independent = sum(
            c * math.prod(row["growth_factors"][i + 1 :]) for i, c in enumerate(row["coupon_cash"])
        )
        assert row["terminal_cash"] == pytest.approx(independent, abs=1e-7)
    periodic = sum(
        (floating["coupon_cash"][i] - fixed["coupon_cash"][i])
        * math.exp(-0.03 * (r["accrual_end"] - start).days / 365)
        for i, r in enumerate(rows)
    )
    assert abs((floating["pv"] - fixed["pv"]) - periodic) > 1000


@pytest.mark.parametrize("spread", [0.0, -0.002, 0.01])
@pytest.mark.parametrize("mode", ["additive", "multiplicative"])
def test_forward_realized_exact_conditions_against_independent_eight_path_enumeration(spread, mode):
    m = model()
    bits = list(itertools.product([0, 1], repeat=3))
    discount = []
    rates = []
    for path in bits:
        r = np.array([0.045 + 0.02 * (2 * sum(path[:i]) - i) for i in range(3)])
        rates.append(r)
        discount.append(np.cumprod(1 / (1 + r)))
    dfs = np.mean(discount, axis=0)
    forwards = np.r_[1, dfs[:-1]] / dfs - 1
    growth = m.compound_growth(forwards, [1] * 3, spread=spread, mode=mode)
    production = m.compound_balances(1e6 * forwards, growth)[-1] * dfs[-1]
    independent = []
    for r, df in zip(rates, discount, strict=True):
        factors = (1 + r) * (1 + spread) if mode == "multiplicative" else 1 + r + spread
        cash = sum(1e6 * r[i] * math.prod(factors[i + 1 :]) for i in range(3))
        independent.append(cash * df[-1])
    exact = np.mean(independent)
    if spread == 0 or mode == "multiplicative":
        assert production == pytest.approx(exact, abs=1e-8)
    else:
        assert abs(production - exact) > 0.5


def test_coupon_and_compound_spreads_are_distinct_and_math_domain():
    m = model()
    rate = np.array([0.04, 0.05])
    accr = np.array([0.5, 0.5])
    spread = 0.002
    a = m.compound_growth(rate, accr, spread=spread, mode="additive")
    b = m.compound_growth(rate, accr, spread=spread, mode="multiplicative")
    assert b - a == pytest.approx(rate * spread * accr**2, abs=1e-15)
    assert m.compound_balances([0, 0], [1.04, 1.05], initial_balance=10)[-1] == pytest.approx(
        10 * 1.04 * 1.05
    )
    with pytest.raises(ValueError):
        m.compound_growth([-3], [0.5])
    with pytest.raises(ValueError):
        m.compound_balances([1], [0])
