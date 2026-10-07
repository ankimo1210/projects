"""Hull21.4: equal probability and the log-grid trinomial approximation."""

import math

import numpy as np
import pytest
from hullkit import _numerical_trees as numerical
from hullkit import bsm
from hullkit.fd import fd_vanilla
from scipy.stats import binom


def test_example_21_6_parameters_and_price():
    result = numerical.equal_probability_lattice(
        0.79, 0.795, 0.06, 0.04, 0.75, 3, yield_rate=0.10, american=True
    )
    assert result["up"] == pytest.approx(1.0098, abs=0.00005)
    assert result["down"] == pytest.approx(0.9703, abs=0.00005)
    assert result["probability"] == pytest.approx(0.5, abs=1e-12)
    assert result["price"] == pytest.approx(0.00258059, abs=1e-8)


def test_figure_21_11_all_ten_stock_and_option_nodes():
    result = numerical.equal_probability_lattice(
        0.79, 0.795, 0.06, 0.04, 0.75, 3, yield_rate=0.10, american=True
    )
    stocks = [[0.79], [0.7978, 0.7665], [0.8056, 0.7740, 0.7437], [0.8136, 0.7817, 0.7510, 0.7216]]
    values = [[0.0026], [0.0052, 0], [0.0106, 0, 0], [0.0186, 0, 0, 0]]
    for actual, source in zip(result["stock"], stocks, strict=True):
        assert actual == pytest.approx(source, abs=0.00005)
    for actual, source in zip(result["option"], values, strict=True):
        assert actual == pytest.approx(source, abs=0.00005)


def test_equal_probability_matches_exact_log_mean_and_variance():
    result = numerical.equal_probability_lattice(100, 100, 0.04, 0.2, 1, 4, yield_rate=0.01)
    log_moves = np.log([result["up"], result["down"]])
    assert log_moves.mean() == pytest.approx((0.04 - 0.01 - 0.2**2 / 2) / 4, abs=1e-12)
    assert np.var(log_moves) == pytest.approx(0.2**2 / 4, abs=1e-12)
    # Matching log moments need not match the arithmetic martingale at finite dt.
    assert abs(np.exp(log_moves).mean() - math.exp((0.04 - 0.01) / 4)) > 1e-7


def test_equal_probability_european_independent_terminal_binomial_sum():
    result = numerical.equal_probability_lattice(100, 105, 0.04, 0.2, 1, 40, yield_rate=0.01)
    ups = np.arange(41)
    terminal = 100 * np.exp((0.04 - 0.01 - 0.2**2 / 2) + (2 * ups - 40) * 0.2 / math.sqrt(40))
    expected = math.exp(-0.04) * np.dot(binom.pmf(ups, 40, 0.5), np.maximum(terminal - 105, 0))
    assert result["price"] == pytest.approx(expected, abs=1e-11)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_equal_probability_bsm_limit(kind):
    result = numerical.equal_probability_lattice(50, 50, 0.05, 0.3, 0.5, 1000, kind=kind)
    reference = (bsm.call_price if kind == "call" else bsm.put_price)(50, 50, 0.05, 0.3, 0.5)
    assert result["price"] == pytest.approx(reference, abs=0.001)


def test_equal_probability_survives_coarse_crr_negative_probability():
    with pytest.raises(ValueError):
        numerical.crr_lattice(50, 50, 0.8, 0.01, 0.5, 1)
    result = numerical.equal_probability_lattice(50, 50, 0.8, 0.01, 0.5, 1)
    assert result["price"] > 0
    assert result["probability"] == pytest.approx(0.5, abs=1e-12)


def test_trinomial_log_moments_and_first_order_variance():
    result = numerical.trinomial_lattice(100, 100, 0.04, 0.2, 1, 10, yield_rate=0.01)
    probabilities = np.array(result["probabilities"])
    move = np.array([result["dx"], 0, -result["dx"]])
    mean = np.dot(probabilities, move)
    second = np.dot(probabilities, move**2)
    assert probabilities.sum() == pytest.approx(1, abs=1e-12)
    assert probabilities[1] == pytest.approx(2 / 3, abs=1e-12)
    assert mean == pytest.approx((0.04 - 0.01 - 0.2**2 / 2) * 0.1, abs=1e-12)
    assert second == pytest.approx(0.2**2 * 0.1, abs=1e-12)
    assert second - mean**2 == pytest.approx(0.2**2 * 0.1 - mean**2, abs=1e-12)


def test_trinomial_independent_log_pde_matrix_power():
    n, dt, sigma, r, q = 5, 0.2, 0.2, 0.04, 0.01
    dx = sigma * math.sqrt(3 * dt)
    drift = r - q - sigma**2 / 2
    # Independently form the spatial generator then a split-discount Euler step.
    points = 2 * n + 3
    diffusion = sigma**2 / (2 * dx**2)
    generator = np.diag(np.full(points, -2 * diffusion))
    generator += np.diag(np.full(points - 1, diffusion + drift / (2 * dx)), 1)
    generator += np.diag(np.full(points - 1, diffusion - drift / (2 * dx)), -1)
    matrix = math.exp(-r * dt) * (np.eye(points) + dt * generator)
    stock = 100 * np.exp(dx * (np.arange(points) - (n + 1)))
    price = (np.linalg.matrix_power(matrix, n) @ np.maximum(stock - 105, 0))[n + 1]
    result = numerical.trinomial_lattice(100, 105, r, sigma, 1, n, yield_rate=q)
    assert result["price"] == pytest.approx(price, abs=1e-11)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_trinomial_european_bsm_limit(kind):
    result = numerical.trinomial_lattice(50, 50, 0.05, 0.3, 0.5, 1000, kind=kind)
    reference = (bsm.call_price if kind == "call" else bsm.put_price)(50, 50, 0.05, 0.3, 0.5)
    assert result["price"] == pytest.approx(reference, abs=0.003)


def test_trinomial_american_independent_cn_pde():
    result = numerical.trinomial_lattice(50, 50, 0.1, 0.4, 5 / 12, 500, kind="put", american=True)
    reference = fd_vanilla(50, 50, 0.1, 0.4, 5 / 12, kind="put", american=True, n_s=800, n_t=1600)
    assert result["price"] == pytest.approx(reference, abs=0.005)


def test_trinomial_negative_probability_is_not_clipped():
    with pytest.raises(ValueError):
        numerical.trinomial_lattice(50, 50, 0.5, 0.01, 0.5, 1)
