"""Hull GE section 12.3: printed spread examples and residual option values."""

import math

import numpy as np
import pytest
from hullkit import _option_strategies as strategies
from hullkit import bsm, fd
from scipy.integrate import quad


def test_example_12_2_call_bull_six_relations():
    result = strategies.strategy_profit(
        [25, 30, 32, 35, 40], strategies.spread_legs("bull_call_spread", [30, 35]), [3, 1]
    )
    assert result["initial_cost"] == pytest.approx(2)
    assert result["payoff"] == pytest.approx([0, 0, 2, 5, 5])
    assert result["profit"] == pytest.approx([-2, -2, 0, 3, 3])


def test_example_12_3_put_bear_six_relations():
    result = strategies.strategy_profit(
        [25, 30, 33, 35, 40], strategies.spread_legs("bear_put_spread", [30, 35]), [3, 1]
    )
    assert result["initial_cost"] == pytest.approx(2)
    assert result["payoff"] == pytest.approx([5, 5, 2, 0, 0])
    assert result["profit"] == pytest.approx([3, 3, 0, -2, -2])


def test_hull_butterfly_cost_loss_breakevens_and_max_profit():
    result = strategies.strategy_profit(
        [50, 55, 56, 60, 64, 65, 70],
        strategies.spread_legs("call_butterfly", [55, 60, 65]),
        [10, 7, 5],
    )
    assert result["initial_cost"] == pytest.approx(1)
    assert result["profit"] == pytest.approx([-1, -1, 0, 4, 0, -1, -1])


@pytest.mark.parametrize(
    "name",
    [
        "bull_call_spread",
        "bear_call_spread",
        "bull_put_spread",
        "bear_put_spread",
        "call_butterfly",
        "put_butterfly",
        "box",
    ],
)
def test_all_same_maturity_spreads_independent_piecewise_and_reversal(name):
    spot = np.array([0, 20, 30, 35, 40, 50, 100.0])
    strikes = [30, 35, 40] if "butterfly" in name else [30, 40]
    legs = strategies.spread_legs(name, strikes)
    result = strategies.strategy_profit(spot, legs, np.ones(len(legs)))
    rising = np.clip(spot - 30, 0, 10)
    independent = {
        "bull_call_spread": rising,
        "bear_call_spread": -rising,
        "bull_put_spread": rising - 10,
        "bear_put_spread": 10 - rising,
        "call_butterfly": np.maximum(5 - np.abs(spot - 35), 0),
        "put_butterfly": np.maximum(5 - np.abs(spot - 35), 0),
        "box": np.full_like(spot, 10),
    }[name]
    assert result["payoff"] == pytest.approx(independent)
    reverse = strategies.strategy_profit(
        spot, strategies.spread_legs(name, strikes, reverse=True), np.ones(len(legs))
    )
    assert reverse["profit"] == pytest.approx(-result["profit"])


@pytest.mark.parametrize("american", [False, True])
def test_business_snapshot_12_1_box_components_and_independent_pde(american):
    result = strategies.spread_value(
        50, [55, 60], 0.08, 0.3, 2 / 12, name="box", american=american, steps=2000
    )
    expected = [0.96, 0.26, 10.00, 5.44] if american else [0.96, 0.26, 9.46, 5.23]
    assert result["leg_prices"] == pytest.approx(expected, abs=0.005)
    pde_prices = [
        fd.fd_vanilla(
            50, strike, 0.08, 0.3, 2 / 12, kind=kind, american=american, n_s=600, n_t=1000
        )
        for _, kind, strike in result["legs"]
    ]
    assert result["leg_prices"] == pytest.approx(pde_prices, abs=0.003)
    pde_box = sum(q * price for (q, _, _), price in zip(result["legs"], pde_prices, strict=True))
    assert result["price"] == pytest.approx(pde_box, abs=0.004)
    bull, bear = (
        result["leg_prices"][0] - result["leg_prices"][1],
        result["leg_prices"][2] - result["leg_prices"][3],
    )
    assert bull == pytest.approx(0.70, abs=0.005)
    assert bear == pytest.approx(4.56 if american else 4.23, abs=0.005)
    if american:
        assert round(bull, 2) + round(bear, 2) == pytest.approx(5.26, abs=1e-12)
        assert result["price"] > 5.10
        assert result["price"] == pytest.approx(5.267, abs=0.002)
    else:
        assert result["price"] == pytest.approx(4.93, abs=0.005)
        assert result["price"] == pytest.approx(5 * math.exp(-0.08 * 2 / 12), abs=1e-12)


@pytest.mark.parametrize(
    "kind,long_strike", [("call", 100), ("put", 100), ("call", 105), ("put", 105)]
)
def test_calendar_and_diagonal_long_leg_independent_remaining_payoff_integral(kind, long_strike):
    spots = np.array([70, 100, 130.0])
    result = strategies.short_expiry_spread(
        spots, 100, long_strike, 0.05, 0.2, 0.25, 1, kind=kind, short_premium=4, long_premium=10
    )
    tau = 0.75
    expected = []
    for spot in spots:
        drift, width = (0.05 - 0.2**2 / 2) * tau, 0.2 * math.sqrt(tau)
        split = (math.log(long_strike / spot) - drift) / width

        def integrand(z, spot=spot, drift=drift, width=width):
            terminal = spot * math.exp(drift + width * z)
            payoff = (
                max(terminal - long_strike, 0) if kind == "call" else max(long_strike - terminal, 0)
            )
            return payoff * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

        expected.append(
            math.exp(-0.05 * tau) * (quad(integrand, -12, split)[0] + quad(integrand, split, 12)[0])
        )
    short_payoff = np.maximum(spots - 100, 0) if kind == "call" else np.maximum(100 - spots, 0)
    assert result["remaining_long_value"] == pytest.approx(expected, abs=1e-8)
    assert result["value"] == pytest.approx(np.array(expected) - short_payoff, abs=1e-8)
    assert result["profit"] == pytest.approx(np.array(expected) - short_payoff - 6, abs=1e-8)
    # The long option's original one-year maturity would be the wrong mark at T1.
    wrong = [
        bsm.call_price(s, long_strike, 0.05, 0.2, 1)
        if kind == "call"
        else bsm.put_price(s, long_strike, 0.05, 0.2, 1)
        for s in spots
    ]
    assert max(abs(np.array(wrong) - result["remaining_long_value"])) > 0.1


def test_calendar_high_stock_residual_value_keeps_discounted_strike():
    result = strategies.short_expiry_spread([0, 1000], 100, 100, 0.05, 0.2, 0.25, 1)
    assert result["value"][0] == pytest.approx(0)
    assert result["value"][1] == pytest.approx(100 * (1 - math.exp(-0.05 * 0.75)), abs=1e-9)


def test_calendar_zero_remaining_time_and_reversed_position():
    forward = strategies.short_expiry_spread(
        [0, 100, 130], 100, 105, 0.05, 0.2, 0.25, 0.25, short_premium=4, long_premium=10
    )
    reverse = strategies.short_expiry_spread(
        [0, 100, 130],
        100,
        105,
        0.05,
        0.2,
        0.25,
        0.25,
        short_premium=4,
        long_premium=10,
        reverse=True,
    )
    assert forward["value"] == pytest.approx([0, 0, -5])
    assert reverse["profit"] == pytest.approx(-forward["profit"])


def test_invalid_spread_order_and_maturity():
    with pytest.raises(ValueError):
        strategies.spread_legs("bull_call_spread", [40, 30])
    with pytest.raises(ValueError):
        strategies.short_expiry_spread([100], 100, 100, 0.05, 0.2, 1, 0.5)
