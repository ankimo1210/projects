"""Hull GE §26.1 packages: zero-cost range forwards and deferred-payment options."""

import math

import numpy as np
import pytest
from hullkit import bsm, packages

SECTION_17_2 = dict(spot=1.32, r=0.02, sigma=0.14, T=0.25, q=0.02)
CASES = [
    dict(spot=1.32, r=0.02, sigma=0.14, T=0.25, q=0.02),
    dict(spot=100.0, r=0.05, sigma=0.20, T=1.0, q=0.02),
    dict(spot=100.0, r=0.01, sigma=0.35, T=2.0, q=0.06),
    dict(spot=50.0, r=0.0, sigma=0.10, T=0.5, q=0.0),
]


def forward(case):
    return case["spot"] * math.exp((case["r"] - case["q"]) * case["T"])


def test_range_forward_reproduces_hull_section_17_2():
    """§26.1 refers to §17.2, where K1=1.3000 gives K2=1.3414 and both options cost 0.0273."""
    result = packages.range_forward(1.30, **SECTION_17_2)
    assert result.call_strike == pytest.approx(1.3414, abs=5e-5)
    assert result.premium == pytest.approx(0.0273, abs=5e-5)
    assert result.forward == pytest.approx(1.32, abs=1e-12)
    assert result.put_strike < result.forward < result.call_strike


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("put_fraction", [0.5, 0.8, 0.95, 0.999])
def test_range_forward_costs_nothing_and_brackets_the_forward(case, put_fraction):
    put_strike = put_fraction * forward(case)
    result = packages.range_forward(put_strike, **case)
    call = bsm.call_price(
        case["spot"], result.call_strike, case["r"], case["sigma"], case["T"], case["q"]
    )
    put = bsm.put_price(case["spot"], put_strike, case["r"], case["sigma"], case["T"], case["q"])
    assert call == pytest.approx(put, rel=1e-10)
    assert result.premium == pytest.approx(put, rel=1e-12)
    assert result.cost == pytest.approx(0.0, abs=1e-10 * result.premium)
    assert put_strike < forward(case) < result.call_strike
    assert result.forward == pytest.approx(forward(case), rel=1e-14)


@pytest.mark.parametrize("case", CASES)
def test_put_strike_at_the_forward_gives_the_forward(case):
    result = packages.range_forward(forward(case), **case)
    assert result.call_strike == pytest.approx(forward(case), rel=1e-12)
    call = bsm.call_price(
        case["spot"], forward(case), case["r"], case["sigma"], case["T"], case["q"]
    )
    assert result.premium == pytest.approx(call, rel=1e-10)


def test_lower_put_strike_needs_a_higher_call_strike():
    strikes = [
        packages.range_forward(k, **SECTION_17_2).call_strike for k in (1.31, 1.25, 1.10, 0.80)
    ]
    assert strikes == sorted(strikes)
    assert strikes[-1] > strikes[0] * 1.1


def test_range_forward_payoff_is_the_call_leg_less_the_put_leg():
    result = packages.range_forward(1.30, **SECTION_17_2)
    grid = np.array([1.0, 1.30, 1.31, 1.34, result.call_strike, 1.5])
    expected = np.maximum(grid - result.call_strike, 0.0) - np.maximum(1.30 - grid, 0.0)
    assert result.payoff(grid) == pytest.approx(expected, abs=1e-15)
    assert result.payoff(grid, side="short") == pytest.approx(-expected, abs=1e-15)
    assert result.payoff(1.32) == 0.0


def test_range_forward_rejects_a_put_strike_above_the_forward():
    with pytest.raises(ValueError, match="put_strike"):
        packages.range_forward(1.33, **SECTION_17_2)
    with pytest.raises(ValueError, match="put_strike"):
        packages.range_forward(0.0, **SECTION_17_2)


def test_range_forward_rejects_an_unknown_side():
    result = packages.range_forward(1.30, **SECTION_17_2)
    with pytest.raises(ValueError, match="side"):
        result.payoff(1.3, side="flat")


@pytest.mark.parametrize("bad", [dict(spot=0.0), dict(sigma=0.0), dict(T=0.0), dict(sigma=-0.1)])
def test_range_forward_rejects_degenerate_inputs(bad):
    args = {**SECTION_17_2, **bad}
    with pytest.raises(ValueError):
        packages.range_forward(1.30, **args)


def test_deferred_amount_is_the_premium_grown_at_the_risk_free_rate():
    assert packages.deferred_amount(0.0393, 0.02, 0.25) == pytest.approx(0.0393 * math.exp(0.005))
    assert packages.deferred_amount(2.0, 0.0, 3.0) == 2.0


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("kind", ["call", "put"])
def test_deferred_option_has_zero_present_value(case, kind):
    strike = 1.05 * forward(case)
    option = packages.deferred_option(kind, strike, **case)
    price = (bsm.call_price if kind == "call" else bsm.put_price)(
        case["spot"], strike, case["r"], case["sigma"], case["T"], case["q"]
    )
    assert option.premium == pytest.approx(price, rel=1e-14)
    assert option.amount == pytest.approx(price * math.exp(case["r"] * case["T"]), rel=1e-14)
    assert price - option.amount * math.exp(-case["r"] * case["T"]) == pytest.approx(0.0, abs=1e-14)


def test_deferred_call_payoff_is_the_option_less_the_deferred_amount():
    option = packages.deferred_option("call", 1.32, **SECTION_17_2)
    grid = np.linspace(1.0, 1.6, 13)
    assert option.payoff(grid) == pytest.approx(
        np.maximum(grid - 1.32, 0.0) - option.amount, abs=1e-15
    )
    assert option.payoff(grid) == pytest.approx(
        np.maximum(grid - 1.32 - option.amount, -option.amount), abs=1e-15
    )
    assert option.breakeven == pytest.approx(1.32 + option.amount)
    assert option.max_loss == option.amount
    assert option.payoff(option.breakeven) == pytest.approx(0.0, abs=1e-15)
    assert option.payoff(0.5) == pytest.approx(-option.amount)


def test_deferred_put_has_its_breakeven_below_the_strike():
    option = packages.deferred_option("put", 1.32, **SECTION_17_2)
    assert option.breakeven == pytest.approx(1.32 - option.amount)
    assert option.payoff(option.breakeven) == pytest.approx(0.0, abs=1e-15)
    assert option.payoff(2.0) == pytest.approx(-option.amount)


@pytest.mark.parametrize("case", CASES)
def test_break_forward_is_a_deferred_call_struck_at_the_forward(case):
    option = packages.break_forward(**case)
    assert option.kind == "call"
    assert option.strike == pytest.approx(forward(case), rel=1e-14)
    put = bsm.put_price(case["spot"], forward(case), case["r"], case["sigma"], case["T"], case["q"])
    assert option.premium == pytest.approx(put, rel=1e-10)
    assert option.amount == pytest.approx(put * math.exp(case["r"] * case["T"]), rel=1e-10)


@pytest.mark.parametrize("case", CASES)
def test_break_forward_is_a_forward_and_a_put_less_the_deferred_amount(case):
    option = packages.break_forward(**case)
    grid = np.linspace(0.5, 1.6, 23) * forward(case)
    parts = (grid - option.strike) + np.maximum(option.strike - grid, 0.0) - option.amount
    assert option.payoff(grid) == pytest.approx(parts, abs=1e-12 * option.strike)


def test_deferred_option_rejects_bad_arguments():
    with pytest.raises(ValueError, match="kind"):
        packages.deferred_option("straddle", 1.32, **SECTION_17_2)
    with pytest.raises(ValueError, match="strike"):
        packages.deferred_option("call", -1.0, **SECTION_17_2)
    with pytest.raises(ValueError):
        packages.deferred_amount(-0.1, 0.02, 0.25)
