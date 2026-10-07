"""Hull GE 14.3: supplied shocks and printed-coefficient Table 14.1 replay."""

import math
from decimal import Decimal

import numpy as np
import pytest
from hullkit import _stochastic_foundations as stochastic
from hullkit.mc import gbm_theory

SHOCKS = [0.52, 1.44, -0.86, 1.46, -0.69, -0.74, 0.21, -1.10, 0.73, 1.16, 2.56]


def test_hull_example_14_3_and_all_twenty_two_table_14_1_cells():
    assert 0.15 * 0.0192 == pytest.approx(0.00288, abs=1e-12)
    assert 0.3 * math.sqrt(0.0192) == pytest.approx(0.0416, abs=0.00005)
    paths = stochastic.stock_paths(
        100, 0.15, 0.3, 0.0192, SHOCKS, step_coefficients=(0.00288, 0.0416)
    )
    starts = paths[0, :-1]
    changes = np.diff(paths[0])
    assert starts == pytest.approx(
        [100, 102.45, 108.88, 105.30, 112.00, 109.11, 106.06, 107.30, 102.69, 106.11, 111.54],
        abs=0.005,
        rel=0,
    )
    assert changes == pytest.approx(
        [2.45, 6.43, -3.58, 6.70, -2.89, -3.04, 1.23, -4.60, 3.41, 5.43, 12.20], abs=0.005, rel=0
    )
    # Independent high-precision cash-change loop; only display values are rounded.
    value = Decimal(100)
    reference = [value]
    for shock in SHOCKS:
        value += value * (Decimal(".00288") + Decimal(".0416") * Decimal(str(shock)))
        reference.append(value)
    assert paths[0] == pytest.approx([float(x) for x in reference], abs=1e-11, rel=0)
    assert paths[0, 10] == pytest.approx(111.54, abs=0.005)  # ten weeks, not the 11th change.


def test_source_rounding_is_explicit_and_euler_can_produce_negative_stock():
    source = stochastic.stock_paths(
        100, 0.15, 0.3, 0.0192, SHOCKS, step_coefficients=(0.00288, 0.0416)
    )
    raw = stochastic.stock_paths(100, 0.15, 0.3, 0.0192, SHOCKS)
    assert [round(source[0, 10], 2), round(raw[0, 10], 2)] == pytest.approx(
        [111.54, 111.53], abs=1e-12
    )
    assert stochastic.stock_paths(100, 0, 0.3, 1, [-4])[0, -1] < 0
    exact = stochastic.stock_paths(100, 0, 0.3, 1, [-4], scheme="exact")
    assert exact[0, -1] > 0


def test_euler_mc_matches_independent_product_moments_with_standard_errors():
    normals = np.random.default_rng(143).standard_normal((30000, 20))
    terminal = stochastic.stock_paths(100, 0.15, 0.3, 0.02, normals)[:, -1]
    mean, variance = stochastic.euler_stock_moments(100, 0.15, 0.3, 0.4, 20)
    assert abs(terminal.mean() - mean) < 6 * terminal.std(ddof=1) / math.sqrt(len(terminal))
    squares = (terminal - mean) ** 2
    assert abs(squares.mean() - variance) < 6 * squares.std(ddof=1) / math.sqrt(len(terminal))


def test_euler_moments_converge_and_zero_volatility_exact_scheme_matches_source_exponential():
    exact_mean, exact_variance = gbm_theory(100, 0.15, 0.3, 1)
    errors = [
        np.abs(
            np.array(stochastic.euler_stock_moments(100, 0.15, 0.3, 1, n))
            - [exact_mean, exact_variance]
        )
        for n in [4, 16, 256]
    ]
    assert np.all(errors[-1] < errors[0] / 40)
    paths = stochastic.stock_paths(100, 0.14, 0, 0.25, [0, 0, 0, 0], scheme="exact")
    assert paths[0] == pytest.approx(100 * np.exp(0.14 * np.arange(5) * 0.25), abs=1e-12)


@pytest.mark.parametrize("steps", [1, 2, 3])
def test_euler_moments_against_gauss_hermite_product_expectation(steps):
    # Independent of the closed form: integrate the Euler product over each normal draw.
    spot, drift, sigma, maturity = 100, 0.15, 0.3, 0.4
    dt = maturity / steps
    nodes, weights = np.polynomial.hermite_e.hermegauss(12)
    weights = weights / weights.sum()
    factor = 1 + drift * dt + sigma * math.sqrt(dt) * nodes
    first, second = (
        (spot * float(weights @ factor) ** steps),
        spot**2 * float(weights @ factor**2) ** steps,
    )
    mean, variance = stochastic.euler_stock_moments(spot, drift, sigma, maturity, steps)
    assert mean == pytest.approx(first, rel=1e-13)
    assert variance == pytest.approx(second - first**2, rel=1e-11)
