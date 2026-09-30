"""Independent two-increment payoff references catch the wrong fixing/discount."""

import importlib
import math

import pytest


def reference():
    return importlib.import_module("johnhull.scripts.build_forward_start_reference")


def test_density_integral_matches_hand_price_and_zero_volatility():
    value, error = reference().integrate_forward_start(100, 0.05, 0.2, 1, 2, 0.03)
    assert value == pytest.approx(8.396807689074635, abs=1e-10)
    assert error < 1e-8
    deterministic, _ = reference().integrate_forward_start(100, 0.05, 0, 1, 2, 0.02)
    assert deterministic == pytest.approx(2.8395619246375, abs=1e-12)


def test_zero_yield_is_invariant_for_the_same_remaining_life():
    immediate, _ = reference().integrate_forward_start(100, 0.05, 0.2, 0, 1)
    delayed, _ = reference().integrate_forward_start(100, 0.05, 0.2, 3, 4)
    assert immediate == pytest.approx(10.450583572185565, abs=1e-10)
    assert delayed == pytest.approx(immediate, abs=1e-10)
    dividend, _ = reference().integrate_forward_start(100, 0.05, 0.2, 2, 3, 0.03)
    base, _ = reference().integrate_forward_start(100, 0.05, 0.2, 0, 1, 0.03)
    assert dividend / base == pytest.approx(math.exp(-0.06), abs=1e-13)


def test_two_time_monte_carlo_prices_the_random_fixing_strike():
    data = reference().build()
    assert len(data["cases"]) == 36
    assert len(data["mc"]) == 3
    for row in data["mc"]:
        assert row["paths"] == 524288
        assert row["standard_error"] > 0
        assert abs(row["price"] - row["reference_price"]) < 6 * row["standard_error"]
    assert data["example"]["price"] == pytest.approx(8.396807689074635, abs=1e-10)


def test_fixed_expiry_curves_reach_zero_and_paths_fix_at_start():
    data = reference().build()
    for curve in data["figure"]["fixed_expiry"]:
        assert curve["price"][-1] == 0
    paths = data["figure"]["contract"]
    at_start = paths["time"].index(paths["market"]["T1"])
    for row in paths["paths"]:
        assert row["strike"] == row["stock"][at_start]
        assert row["payoff"] == max(row["stock"][-1] - row["strike"], 0)
