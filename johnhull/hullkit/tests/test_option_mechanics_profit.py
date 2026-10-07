"""Hull §10.1: printed long-option cashflows and independent exercise accounting."""

import importlib
from fractions import Fraction

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._option_mechanics")


def test_printed_call_cashflows_and_exercise_despite_net_loss():
    row = model().option_cashflows([115, 120, 102, 95], 100, 5, multiplier=100)
    assert row["premium_cashflow"] == pytest.approx([-500] * 4)
    assert row["per_unit_payoff"] == pytest.approx([15, 20, 2, 0])
    assert row["payoff"] == pytest.approx([1500, 2000, 200, 0])
    assert row["profit"] == pytest.approx([1000, 1500, -300, -500])
    assert row["unexercised_profit"] == pytest.approx([-500] * 4)
    assert row["profit"][2] - row["unexercised_profit"][2] == pytest.approx(200)


def test_printed_put_cashflows_and_premium_loss():
    row = model().option_cashflows([55, 70, 80], 70, 7, kind="put", multiplier=100)
    assert row["premium_cashflow"] == pytest.approx([-700] * 3)
    assert row["per_unit_payoff"] == pytest.approx([15, 0, 0])
    assert row["payoff"] == pytest.approx([1500, 0, 0])
    assert row["profit"] == pytest.approx([800, -700, -700])


@pytest.mark.parametrize("kind,strike,premium", [("call", 100, 5), ("put", 70, 7)])
def test_independent_physical_exercise_cash_ledger(kind, strike, premium):
    spots = np.array([0, 55, 63, 70, 98, 100, 102, 105, 115, 120, 180])
    actual = model().option_cashflows(spots, strike, premium, kind=kind, quantity=3, multiplier=100)
    expected = []
    for spot in spots:
        # Buy and immediately sell stock, or sell stock and repurchase it;
        # exercise only when those physical cashflows are profitable.
        cash = Fraction(strike) - Fraction(int(spot))
        if kind == "call":
            cash = -cash
        exercise = cash if cash > 0 else Fraction(0)
        expected.append(float(300 * (exercise - premium)))
    assert np.allclose(actual["profit"], expected, atol=1e-12, rtol=1e-12)
    breakeven = strike + premium if kind == "call" else strike - premium
    assert model().option_cashflows(breakeven, strike, premium, kind=kind)[
        "profit"
    ] == pytest.approx(0)


@pytest.mark.parametrize(
    "kwargs",
    [{"multiplier": 0}, {"multiplier": -100}, {"premium": np.nan}, {"strike": np.inf}],
)
def test_mathematically_undefined_cashflows_rejected(kwargs):
    arguments = dict(spot=100, strike=100, premium=5)
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        model().option_cashflows(**arguments)
