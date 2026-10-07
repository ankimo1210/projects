"""Hull GE section 12.5: butterfly hats, interpolation and bounded support."""

import math

import numpy as np
import pytest
from hullkit import _option_strategies as strategies
from hullkit import bsm, payoffs
from scipy.integrate import quad


def test_symbolic_butterfly_width_h_has_height_h_and_normalization():
    spots = np.array([0, 90, 95, 100, 105, 110, 200.0])
    plain = strategies.butterfly_spike(spots, 100, 5)
    unit = strategies.butterfly_spike(spots, 100, 5, height=1)
    assert plain["payoff"] == pytest.approx(np.maximum(5 - np.abs(spots - 100), 0))
    assert unit["payoff"] == pytest.approx(plain["payoff"] / 5)
    assert unit["payoff"][3] == pytest.approx(1)


def test_nonuniform_signed_nodes_against_independent_linear_interpolation():
    spots = np.linspace(0, 100, 501)
    result = strategies.replicate_payoff(spots, [20, 30, 50], [2, -1, 3])
    expected = np.interp(spots, [10, 20, 30, 50, 70], [0, 2, -1, 3, 0], left=0, right=0)
    assert result["payoff"] == pytest.approx(expected, abs=2e-13)
    at_nodes = strategies.replicate_payoff([20, 30, 50], [20, 30, 50], [2, -1, 3])
    assert at_nodes["payoff"] == pytest.approx([2, -1, 3], abs=1e-13)


def test_smooth_target_h_halving_off_grid_convergence_on_declared_interval():
    spots = np.linspace(60, 140, 2001)

    def target(s):
        return np.exp(-0.5 * ((s - 100) / 12) ** 2)

    coarse_grid, fine_grid = np.arange(60, 141, 5), np.arange(60, 141, 2.5)
    coarse = strategies.replicate_payoff(spots, coarse_grid, target(coarse_grid))["payoff"]
    fine = strategies.replicate_payoff(spots, fine_grid, target(fine_grid))["payoff"]
    coarse_error, fine_error = (
        np.max(abs(coarse - target(spots))),
        np.max(abs(fine - target(spots))),
    )
    assert fine_error < 0.3 * coarse_error
    # Linear interpolation error <= h^2 max|f''|/8; Gaussian curvature <= 1/12^2.
    assert fine_error <= 2.5**2 / (8 * 12**2) + 1e-12
    # This convergence claim covers [60,140]; the finite construction has explicit zero tails.
    outside = strategies.replicate_payoff([0, 50, 150, 1000], coarse_grid, target(coarse_grid))
    assert outside["payoff"] == pytest.approx(np.zeros(4), abs=1e-12)


def test_zero_strike_boundary_uses_cash_stock_instead_of_negative_option_strikes():
    spots = np.array([0, 2.5, 5, 7.5, 10, 12.5, 15, 30])
    result = strategies.replicate_payoff(spots, [0, 5, 10], [1, 2, 3])
    expected = np.interp(spots, [-5, 0, 5, 10, 15], [0, 1, 2, 3, 0])
    assert result["payoff"] == pytest.approx(expected, abs=1e-12)
    assert payoffs.strategy_payoff(spots, result["legs"]) + result["cash"] == pytest.approx(
        expected, abs=1e-12
    )
    assert all(strike >= 0 for _, kind, strike in result["legs"] if kind == "call")


def test_static_call_portfolio_value_equals_independent_payoff_integration():
    knots, values = [20, 30, 50], [2, -1, 3]
    result = strategies.replicate_payoff([30], knots, values)
    price = result["cash"] * math.exp(-0.05)
    for quantity, kind, strike in result["legs"]:
        price += quantity * (30 if kind == "stock" else bsm.call_price(30, strike, 0.05, 0.3, 1))

    def density_payoff(stock):
        z = (math.log(stock / 30) - (0.05 - 0.3**2 / 2)) / 0.3
        density = math.exp(-z * z / 2) / (stock * 0.3 * math.sqrt(2 * math.pi))
        return float(np.interp(stock, [10, 20, 30, 50, 70], [0, 2, -1, 3, 0])) * density

    expectation = math.exp(-0.05) * quad(density_payoff, 10, 70, points=knots, epsabs=1e-11)[0]
    assert price == pytest.approx(expectation, abs=1e-10)


def test_undefined_spike_width_and_duplicate_knots():
    with pytest.raises(ValueError):
        strategies.butterfly_spike([100], 100, 0)
    with pytest.raises(ValueError):
        strategies.replicate_payoff([30], [20, 20, 30], [1, 2, 3])
