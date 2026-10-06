"""Hull 21.1: source lattice, exercise decisions and tree Greek estimates."""

import math

import numpy as np
import pytest
from hullkit import _numerical_trees as numerical
from hullkit import bsm
from hullkit._binomial_foundations import small_tree_stopping_values
from hullkit.fd import fd_vanilla


def test_example_21_1_all_twenty_one_stock_and_option_nodes():
    result = numerical.crr_lattice(50, 50, 0.1, 0.4, 5 / 12, 5, kind="put", american=True)
    stocks = [
        [50],
        [56.12, 44.55],
        [62.99, 50, 39.69],
        [70.70, 56.12, 44.55, 35.36],
        [79.35, 62.99, 50, 39.69, 31.50],
        [89.07, 70.70, 56.12, 44.55, 35.36, 28.07],
    ]
    options = [
        [4.49],
        [2.16, 6.96],
        [0.64, 3.77, 10.36],
        [0, 1.30, 6.38, 14.64],
        [0, 0, 2.66, 10.31, 18.50],
        [0, 0, 0, 5.45, 14.64, 21.93],
    ]
    for actual, printed in zip(result["stock"], stocks, strict=True):
        assert actual == pytest.approx(printed, abs=0.005)
    for actual, printed in zip(result["option"], options, strict=True):
        assert actual == pytest.approx(printed, abs=0.005)
    assert result["probability"] == pytest.approx(0.5073, abs=0.00005)
    assert result["continuation"][4][3] == pytest.approx(9.90, abs=0.005)
    assert result["exercise"][4][3]
    assert not result["exercise"][2][2]
    assert result["continuation"][2][2] == pytest.approx(10.36, abs=0.005)


@pytest.mark.parametrize("steps,printed", [(30, 4.263), (50, 4.272), (100, 4.278), (500, 4.283)])
def test_example_21_1_source_convergence_prices(steps, printed):
    result = numerical.crr_lattice(50, 50, 0.1, 0.4, 5 / 12, steps, kind="put", american=True)
    assert result["price"] == pytest.approx(printed, abs=0.0005)


def test_american_lattice_independent_all_stopping_policies():
    result = numerical.crr_lattice(50, 50, 0.1, 0.4, 5 / 12, 5, kind="put", american=True)
    reference = small_tree_stopping_values(
        50, 50, 0.1, 5 / 12, 5, result["up"], result["down"], kind="put"
    )
    assert result["price"] == pytest.approx(reference["price"], abs=1e-11)


def test_american_lattice_independent_finite_difference_limit():
    result = numerical.crr_lattice(50, 50, 0.1, 0.4, 5 / 12, 500, kind="put", american=True)
    reference = fd_vanilla(50, 50, 0.1, 0.4, 5 / 12, kind="put", american=True, n_s=800, n_t=1600)
    assert result["price"] == pytest.approx(reference, abs=0.004)


def test_example_21_2_greeks_and_units_at_five_and_fifty_steps():
    five = numerical.tree_greek_details(50, 50, 0.1, 0.4, 5 / 12, 5, kind="put", american=True)
    assert five["delta"] == pytest.approx(-0.414530, abs=1e-6)
    assert five["gamma"] == pytest.approx(0.034146, abs=1e-6)
    assert five["theta_year"] == pytest.approx(-4.30390, abs=1e-5)
    fifty = numerical.tree_greek_details(50, 50, 0.1, 0.4, 5 / 12, 50, kind="put", american=True)
    assert fifty["delta"] == pytest.approx(-0.415, abs=0.0005)
    assert fifty["gamma"] == pytest.approx(0.034, abs=0.0005)
    assert fifty["theta_day"] == pytest.approx(-0.0117, abs=0.00005)
    assert fifty["vega_per_point"] == pytest.approx(0.123, abs=0.0005)
    assert fifty["rho_per_point"] == pytest.approx(-0.072, abs=0.0005)
    assert fifty["theta_day"] * 365 == pytest.approx(fifty["theta_year"], abs=1e-12)
    assert fifty["delta_time"] == pytest.approx(5 / 12 / 50, abs=1e-12)
    assert fifty["gamma_time"] == pytest.approx(2 * 5 / 12 / 50, abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_european_tree_greeks_independent_analytic_limit(kind):
    result = numerical.tree_greek_details(
        50, 50, 0.05, 0.3, 0.5, 1000, kind=kind, vol_bump=1e-5, rate_bump=1e-5
    )
    delta = bsm.call_delta if kind == "call" else bsm.put_delta
    theta = bsm.call_theta if kind == "call" else bsm.put_theta
    assert result["delta"] == pytest.approx(delta(50, 50, 0.05, 0.3, 0.5), abs=0.0005)
    assert result["gamma"] == pytest.approx(bsm.gamma(50, 50, 0.05, 0.3, 0.5), abs=0.00005)
    assert result["theta_year"] == pytest.approx(theta(50, 50, 0.05, 0.3, 0.5), abs=0.01)
    assert result["vega"] == pytest.approx(bsm.vega(50, 50, 0.05, 0.3, 0.5), abs=0.01)
    assert result["rho"] == pytest.approx(
        (bsm.call_rho if kind == "call" else bsm.put_rho)(50, 50, 0.05, 0.3, 0.5), abs=0.01
    )


def test_every_preexpiry_decision_matches_complementarity_conditions():
    result = numerical.crr_lattice(50, 50, 0.1, 0.4, 5 / 12, 5, kind="put", american=True)
    for level in range(5):
        value = result["option"][level]
        immediate = np.maximum(50 - result["stock"][level], 0)
        continuation = result["continuation"][level]
        assert np.all(value >= immediate - 1e-12) and np.all(value >= continuation - 1e-12)
        assert np.allclose((value - immediate) * (value - continuation), 0, atol=1e-11)


def test_invalid_time_or_insufficient_levels_for_greeks():
    with pytest.raises(ValueError):
        numerical.crr_lattice(50, 50, 0.1, 0.4, -1, 5)
    with pytest.raises(ValueError):
        numerical.tree_greek_details(50, 50, 0.1, 0.4, 5 / 12, 1)
