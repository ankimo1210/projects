"""Hull GE section 12.1: note funding, participation and independent expectation."""

import math

import numpy as np
import pytest
from hullkit import _option_strategies as strategies
from scipy.integrate import quad
from scipy.optimize import brentq


def expected_call(spot, strike, rate, vol, maturity, dividend_yield):
    drift = (rate-dividend_yield-vol**2/2)*maturity
    width = vol*math.sqrt(maturity)
    split = (math.log(strike/spot)-drift)/width
    def cash(z):
        terminal = spot*math.exp(drift+width*z)
        return (terminal-strike)*math.exp(-z*z/2)/math.sqrt(2*math.pi)
    return math.exp(-rate*maturity)*quad(cash, max(split, -12), 12, epsabs=1e-9)[0]


def test_hull_example_12_1_bond_budget_and_volatility_threshold():
    note = strategies.principal_note([900, 1000, 1200], 1000, 1000, 1000, .06, .15, 3, q=.015)
    assert note["bond_cost"] == pytest.approx(835.27, abs=.005)
    assert note["option_budget"] == pytest.approx(164.73, abs=.005)
    assert note["payoff"] == pytest.approx([1000, 1000, 1200])
    limit = strategies.principal_note_volatility_limit(1000, 1000, 1000, .06, 3, q=.015)
    assert limit == pytest.approx(.14937164, abs=5e-8)
    assert .14 < limit < .15
    independent = brentq(lambda vol: expected_call(1000, 1000, .06, vol, 3, .015)-(1000-1000*math.exp(-.18)), .1, .2)
    assert limit == pytest.approx(independent, abs=1e-9)
    # Printed "about 15%" does not say exactly 15% is funded.
    assert note["cash_surplus"] < 0


@pytest.mark.parametrize("rate,vol,maturity,printed_budget,printed_price", [
    (.06, .25, 3, 164.73, 221), (.03, .15, 3, 86.07, 119),
    (.03, .15, 10, 259.18, 217), (.03, .15, 20, 451.19, 281),
])
def test_hull_note_variants_printed_funds_and_call_prices(rate, vol, maturity, printed_budget, printed_price):
    note = strategies.principal_note([1000], 1000, 1000, 1000, rate, vol, maturity, q=.015)
    assert note["option_budget"] == pytest.approx(printed_budget, abs=.005)
    assert note["option_price"] == pytest.approx(printed_price, abs=.5)
    assert note["option_price"] == pytest.approx(expected_call(1000, 1000, rate, vol, maturity, .015), abs=1e-8)


def test_no_dividend_full_atm_participation_exceeds_available_funds():
    note = strategies.principal_note([0, 1000, 2000], 1000, 1000, 1000, .06, .25, 3)
    # Independent replication: call minus put = S-PV(K); positive put consumes extra cash.
    budget = 1000-1000*math.exp(-.18)
    assert note["option_price"] > budget
    assert note["cost"] > 1000
    assert note["affordable_participation"] < 1


def test_fractional_participation_and_nominal_profit_convention():
    note = strategies.principal_note([0, 50, 70], 50, 1000, 1000, .05, .2, 1, participation=10)
    assert note["payoff"] == pytest.approx([1000, 1000, 1200])
    assert note["profit"] == pytest.approx([0, 0, 200])
    assert note["cost"] == pytest.approx(note["bond_cost"]+10*note["option_price"])
    assert note["cash_surplus"] == pytest.approx(1000-note["cost"])


def test_zero_vol_call_and_negative_rate_funding_are_reported():
    free = strategies.principal_note([0, 40], 40, 100, 100, .05, 0, 1, strike=100)
    assert free["option_price"] == pytest.approx(0)
    assert math.isinf(free["affordable_participation"])
    expensive_bond = strategies.principal_note([100], 100, 100, 100, -.05, .2, 1)
    assert expensive_bond["option_budget"] < 0
    assert expensive_bond["affordable_participation"] is None


@pytest.mark.parametrize("maturity,participation", [(-1, 1), (1, -1)])
def test_undefined_note_inputs(maturity, participation):
    with pytest.raises(ValueError):
        strategies.principal_note(np.array([1000]), 1000, 1000, 1000, .06, .15, maturity, participation=participation)


def test_no_dividend_note_is_unaffordable_at_every_volatility_while_the_yield_funds_it():
    # Hull's claim rests on c >= S-K*exp(-rT), which equals the budget when K=S=principal.
    for rate in (.02, .06):
        for maturity in (1, 3, 10):
            for vol in (1e-4, .05, .25, .6):
                note = strategies.principal_note([1000], 1000, 1000, 1000, rate, vol, maturity)
                assert note["option_price"] >= note["option_budget"]-1e-9
                assert note["affordable_participation"] <= 1+1e-12
    assert strategies.principal_note_volatility_limit(1000, 1000, 1000, .06, 3) == 0
    assert strategies.principal_note([1000], 1000, 1000, 1000, .06, .10, 3, q=.015)["affordable_participation"] > 1
