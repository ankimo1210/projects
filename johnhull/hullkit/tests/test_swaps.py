"""Tests for hullkit.swaps (Hull 11e Ch.7)."""

import math

import numpy as np
import pytest
from hullkit import rates, swaps

# upward-sloping test curve (continuous zeros)
CURVE = ([0.5, 1.0, 1.5, 2.0, 3.0], [0.020, 0.024, 0.027, 0.029, 0.032])
PAY_TIMES = [0.5, 1.0, 1.5, 2.0]


def _simple_rate_to(t1, curve):
    # curve-consistent simple rate for the period (0, t1)
    from hullkit import rates

    z1 = rates.zero_interp(t1, *curve)
    return (math.exp(z1 * t1) - 1.0) / t1


def test_par_swap_has_zero_value_both_ways():
    s = swaps.swap_rate(PAY_TIMES, CURVE)
    r1 = _simple_rate_to(0.5, CURVE)
    v_bonds = swaps.irs_value_bonds(100.0, s, PAY_TIMES, CURVE, next_float_rate=r1)
    v_fras = swaps.irs_value_fras(100.0, s, PAY_TIMES, CURVE, next_float_rate=r1)
    assert v_bonds == pytest.approx(0.0, abs=1e-9)
    assert v_fras == pytest.approx(0.0, abs=1e-9)


def test_bonds_equals_fras_off_market():
    r1 = _simple_rate_to(0.5, CURVE)
    for s_fixed in (0.01, 0.03, 0.05):
        v_b = swaps.irs_value_bonds(250.0, s_fixed, PAY_TIMES, CURVE, next_float_rate=r1)
        v_f = swaps.irs_value_fras(250.0, s_fixed, PAY_TIMES, CURVE, next_float_rate=r1)
        assert v_b == pytest.approx(v_f, abs=1e-10)


def test_swap_rate_flat_curve_hand_value():
    flat = ([0.5, 1.0, 1.5, 2.0], [0.03, 0.03, 0.03, 0.03])
    s = swaps.swap_rate([0.5, 1.0, 1.5, 2.0], flat)
    # hand: (1 - e^{-0.06}) / (0.5 * (e^{-0.015}+e^{-0.03}+e^{-0.045}+e^{-0.06}))
    num = 1.0 - math.exp(-0.06)
    den = 0.5 * sum(math.exp(-0.03 * t) for t in (0.5, 1.0, 1.5, 2.0))
    assert s == pytest.approx(num / den, abs=1e-12)
    # flat continuous 3% -> par semiannual simple rate slightly above 3%
    assert 0.030 < s < 0.0305


def test_currency_swap_hull_example_7_3():
    # Hull 11e Example 7.2/7.3: pay $4% on $10M, receive yen 3% on 1,200M yen,
    # USD curve 2.5% cc flat, JPY 1.5% cc flat, S0 = 1/110 USD/JPY.
    # currency_swap_value is receive-domestic; the receive-yen side is the negative.
    v_receive_dollar = swaps.currency_swap_value(
        [1.0, 2.0, 3.0],
        [0.4, 0.4, 10.4],
        ([1.0, 2.0, 3.0], [0.025, 0.025, 0.025]),
        [1.0, 2.0, 3.0],
        [36.0, 36.0, 1236.0],
        ([1.0, 2.0, 3.0], [0.015, 0.015, 0.015]),
        1.0 / 110.0,
    )
    assert -v_receive_dollar == pytest.approx(0.9628, abs=1.5e-3)  # Hull 0.9629


def test_receive_fixed_loses_value_when_rates_rise():
    s = swaps.swap_rate(PAY_TIMES, CURVE)
    r1 = _simple_rate_to(0.5, CURVE)
    bumped = (CURVE[0], [z + 0.01 for z in CURVE[1]])
    r1_b = _simple_rate_to(0.5, bumped)
    v0 = swaps.irs_value_bonds(100.0, s, PAY_TIMES, CURVE, next_float_rate=r1)
    v1 = swaps.irs_value_bonds(100.0, s, PAY_TIMES, bumped, next_float_rate=r1_b)
    assert v1 < v0 - 1e-6


def test_discount_basic():
    assert swaps.discount(1.0, ([1.0], [0.05])) == pytest.approx(np.exp(-0.05), abs=1e-12)


def test_discount_rejects_a_malformed_curve_like_rates_discount_factor():
    """`swaps.discount` must not be a validation-free copy of `rates.discount_factor`.

    Both compute P(0,t) = exp(-z(t) t) from a (times, zeros) curve. The rates
    version validates the curve; the swaps one used to skip that, so an
    unsorted or non-finite curve produced a plausible-looking discount factor
    and every swap value built on it was quietly wrong.
    """
    good = ([0.5, 1.0, 2.0], [0.02, 0.025, 0.03])
    assert swaps.discount(1.0, good) == pytest.approx(rates.discount_factor(1.0, good), abs=1e-15)

    for bad in (
        ([1.0, 0.5, 2.0], [0.02, 0.025, 0.03]),  # unsorted pillars
        ([0.5, 1.0, 2.0], [0.02, float("nan"), 0.03]),  # missing quote
        ([-0.5, 1.0], [0.02, 0.03]),  # negative maturity
    ):
        with pytest.raises(ValueError):
            swaps.discount(1.0, bad)


# Hull Example 7.1: a seasoned swap valued 0.3y into a 0.5y accrual period.
EX71_TIMES = [0.2, 0.7, 1.2]
EX71_CURVE = (EX71_TIMES, [0.028, 0.032, 0.034])
EX71_NEXT_FLOAT = 0.02516  # 2.50% continuous -> 2.516% semiannual, as printed


def test_seasoned_swap_reproduces_hull_example_7_1():
    # Receive-fixed value; Hull's pay-fixed institution holds +0.292 (in $ millions).
    v_bonds = swaps.irs_value_bonds(
        100.0, 0.03, EX71_TIMES, EX71_CURVE, next_float_rate=EX71_NEXT_FLOAT, first_accrual=0.5
    )
    v_fras = swaps.irs_value_fras(
        100.0, 0.03, EX71_TIMES, EX71_CURVE, next_float_rate=EX71_NEXT_FLOAT, first_accrual=0.5
    )
    assert v_bonds == pytest.approx(-0.292, abs=5e-4)
    assert v_fras == pytest.approx(v_bonds, abs=1e-10)
    # direct cash-flow valuation: full 1.5 fixed coupons against the preset float
    df = np.exp(-np.asarray(EX71_TIMES) * np.asarray(EX71_CURVE[1]))
    direct = 1.5 * df.sum() + 100.0 * df[-1] - 100.0 * (1.0 + EX71_NEXT_FLOAT * 0.5) * df[0]
    assert v_bonds == pytest.approx(direct, abs=1e-10)


def test_first_accrual_defaults_to_valuation_on_a_reset_date():
    r1 = _simple_rate_to(0.5, CURVE)
    for pricer in (swaps.irs_value_bonds, swaps.irs_value_fras):
        base = pricer(100.0, 0.03, PAY_TIMES, CURVE, next_float_rate=r1)
        explicit = pricer(100.0, 0.03, PAY_TIMES, CURVE, next_float_rate=r1, first_accrual=0.5)
        assert explicit == pytest.approx(base, abs=1e-12)


def test_seasoned_swap_rejects_inconsistent_first_accrual():
    with pytest.raises(ValueError, match="first_accrual"):
        swaps.irs_value_fras(100.0, 0.03, EX71_TIMES, EX71_CURVE, first_accrual=0.5)
    with pytest.raises(ValueError, match="first_accrual"):
        swaps.irs_value_bonds(
            100.0, 0.03, EX71_TIMES, EX71_CURVE, next_float_rate=EX71_NEXT_FLOAT, first_accrual=0.0
        )
