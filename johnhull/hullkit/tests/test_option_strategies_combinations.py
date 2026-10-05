"""Hull GE section 12.4: straddle example, tail slopes and premium effects."""

import math

import numpy as np
import pytest
from hullkit import _option_strategies as strategies


def test_hull_straddle_s69_k70_six_relations():
    result = strategies.combination_profile([69, 70, 90, 55], "straddle", [70], [4, 3])
    assert result["initial_cost"] == pytest.approx(7)
    assert result["payoff"] == pytest.approx([1, 0, 20, 15])
    assert result["profit"] == pytest.approx([-6, -7, 13, 8])
    assert result["break_evens"] == pytest.approx([63, 77])  # Derived, not printed.


@pytest.mark.parametrize("name,call_weight,put_weight", [("straddle", 1, 1), ("strip", 1, 2), ("strap", 2, 1)])
def test_combinations_independent_piecewise_slopes_and_reverse(name, call_weight, put_weight):
    spots = np.array([0, 50, 60, 70, 80, 90, 100.])
    result = strategies.combination_profile(spots, name, [70], [4, 3])
    expected = np.where(spots < 70, put_weight*(70-spots), call_weight*(spots-70))
    cost = 4*call_weight+3*put_weight
    assert result["payoff"] == pytest.approx(expected)
    assert result["profit"] == pytest.approx(expected-cost)
    assert result["left_slope"] == pytest.approx(-put_weight)
    assert result["right_slope"] == pytest.approx(call_weight)
    assert result["minimum_profit"] == pytest.approx(-cost)
    assert math.isinf(result["maximum_profit"])
    reverse = strategies.combination_profile(spots, name, [70], [4, 3], reverse=True)
    assert reverse["profit"] == pytest.approx(-result["profit"])
    assert reverse["maximum_profit"] == pytest.approx(cost)
    assert reverse["minimum_profit"] == -math.inf
    # Downside is finite at nonnegative stock S=0; only the upward tail is unbounded.
    assert reverse["zero_stock_profit"] == pytest.approx(cost-70*put_weight)


def test_strangle_plateau_and_same_premium_wider_strikes_need_larger_move():
    spots = np.array([0, 58, 65, 70, 75, 82, 100.])
    result = strategies.combination_profile(spots, "strangle", [65, 75], [3, 4])
    independent = np.where(spots < 65, 65-spots, np.where(spots > 75, spots-75, 0))
    assert result["payoff"] == pytest.approx(independent)
    assert result["break_evens"] == pytest.approx([58, 82])
    wider = strategies.combination_profile(spots, "strangle", [60, 80], [3, 4])
    assert wider["break_evens"] == pytest.approx([53, 87])  # Same quoted cost deliberately held fixed.


def test_business_snapshot_12_2_higher_premium_lowers_long_profit_only():
    original = strategies.combination_profile([50, 70, 90], "straddle", [70], [4, 3])
    expensive = strategies.combination_profile([50, 70, 90], "straddle", [70], [8, 6])
    assert expensive["payoff"] == pytest.approx(original["payoff"])
    assert expensive["profit"] == pytest.approx(original["profit"]-7)


def test_unattainable_negative_stock_breakeven_and_free_strangle_interval():
    expensive = strategies.combination_profile([0, 10, 50], "straddle", [10], [20, 20])
    assert expensive["break_evens"] == pytest.approx([50])
    free = strategies.combination_profile([30, 35, 40], "strangle", [30, 40], [0, 0])
    assert free["zero_profit_interval"] == pytest.approx((30, 40))
    assert free["profit"] == pytest.approx([0, 0, 0])
