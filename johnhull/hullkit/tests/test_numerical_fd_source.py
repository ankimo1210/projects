"""Hull21.8 source grids, independent valuation and spatial/time diagnostics."""

import math

import numpy as np
import pytest
from hullkit import _numerical_fd as numerical
from hullkit import _numerical_trees as trees
from hullkit import bsm
from scipy.integrate import quad
from scipy.stats import norm

# Hull GE pp503/505, descending S=100,95,...,40; lower rows are intrinsic.
IMPLICIT_TOP = np.array(
    [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0.02, 0.02, 0.01, 0.01, 0, 0, 0, 0, 0, 0, 0],
        [0.05, 0.04, 0.03, 0.02, 0.01, 0.01, 0, 0, 0, 0, 0],
        [0.09, 0.07, 0.05, 0.03, 0.02, 0.01, 0.01, 0, 0, 0, 0],
        [0.16, 0.12, 0.09, 0.07, 0.04, 0.03, 0.02, 0.01, 0, 0, 0],
        [0.27, 0.22, 0.17, 0.13, 0.09, 0.06, 0.03, 0.02, 0.01, 0, 0],
        [0.47, 0.39, 0.32, 0.25, 0.18, 0.13, 0.08, 0.04, 0.02, 0, 0],
        [0.82, 0.71, 0.60, 0.49, 0.38, 0.28, 0.19, 0.11, 0.05, 0.02, 0],
        [1.42, 1.27, 1.11, 0.95, 0.78, 0.62, 0.45, 0.30, 0.16, 0.05, 0],
        [2.43, 2.24, 2.05, 1.83, 1.61, 1.36, 1.09, 0.81, 0.51, 0.22, 0],
        [4.07, 3.88, 3.67, 3.45, 3.19, 2.91, 2.57, 2.17, 1.66, 0.99, 0],
        [6.58, 6.44, 6.29, 6.13, 5.96, 5.77, 5.57, 5.36, 5.17, 5.02, 5],
        [10.15, 10.10, 10.05, 10.01, 10, 10, 10, 10, 10, 10, 10],
    ]
)
EXPLICIT_TOP = np.array(
    [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0.06, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [-0.11, 0.05, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0.28, -0.05, 0.05, 0, 0, 0, 0, 0, 0, 0, 0],
        [-0.13, 0.20, 0, 0.05, 0, 0, 0, 0, 0, 0, 0],
        [0.46, 0.06, 0.20, 0.04, 0.06, 0, 0, 0, 0, 0, 0],
        [0.32, 0.46, 0.23, 0.25, 0.10, 0.09, 0, 0, 0, 0, 0],
        [0.91, 0.68, 0.63, 0.44, 0.37, 0.21, 0.14, 0, 0, 0, 0],
        [1.48, 1.37, 1.17, 1.02, 0.81, 0.65, 0.42, 0.27, 0, 0, 0],
        [2.59, 2.39, 2.21, 1.99, 1.77, 1.50, 1.24, 0.90, 0.59, 0, 0],
        [4.26, 4.08, 3.89, 3.68, 3.44, 3.18, 2.87, 2.53, 2.07, 1.56, 0],
        [6.76, 6.61, 6.47, 6.31, 6.15, 5.96, 5.75, 5.50, 5.24, 5, 5],
        [10.28, 10.20, 10.13, 10.06, 10.01, 10, 10, 10, 10, 10, 10],
    ]
)
LOWER_ROWS = np.repeat(np.arange(15, 55, 5)[:, None], 11, axis=1)


def source_grid(method="implicit", american=True, **kwargs):
    return numerical.fd_grid(
        50,
        50,
        0.1,
        0.4,
        5 / 12,
        20,
        10,
        s_max=100,
        method=method,
        kind="put",
        american=american,
        **kwargs,
    )


def independent_payoff_integral(spot, strike, rate, vol, maturity, q, kind):
    sign = 1 if kind == "call" else -1
    cutoff = (math.log(strike / spot) - (rate - q - vol**2 / 2) * maturity) / (
        vol * math.sqrt(maturity)
    )

    def integrand(z):
        terminal = spot * math.exp(
            (rate - q - vol**2 / 2) * maturity + vol * math.sqrt(maturity) * z
        )
        return max(sign * (terminal - strike), 0) * norm.pdf(z)

    interval = (cutoff, 11) if kind == "call" else (-11, cutoff)
    return math.exp(-rate * maturity) * quad(integrand, *interval, epsabs=1e-11)[0]


def test_table_21_4_all_231_cells_and_example_21_10():
    grid = source_grid()
    printed = np.vstack((IMPLICIT_TOP, LOWER_ROWS))
    assert grid["values"].T[::-1] == pytest.approx(printed, abs=0.005)
    assert grid["price"] == pytest.approx(4.067186, abs=5e-7)
    assert grid["stock"] == pytest.approx(np.arange(0, 101, 5), abs=1e-12)
    assert grid["times"] == pytest.approx(np.linspace(0, 5 / 12, 11), abs=1e-12)


def test_table_21_5_all_231_cells_preserves_unstable_negative_prices():
    grid = source_grid("explicit", obstacle="source")
    printed = np.vstack((EXPLICIT_TOP, LOWER_ROWS))
    actual = grid["values"].T[::-1]
    tolerance = np.full(printed.shape, 0.005)
    # S75,t0 and S60,t2: Decimal45 confirms two source rounding-boundary cells.
    tolerance[5, 0] = tolerance[8, 2] = 0.0051
    assert np.all(np.abs(actual - printed) <= tolerance)
    assert grid["price"] == pytest.approx(4.256804, abs=5e-7)
    assert actual[2, 0] == pytest.approx(-0.106732, abs=5e-7)
    assert actual[4, 0] == pytest.approx(-0.134077, abs=5e-7)
    assert not grid["weights_nonnegative"]
    j = np.arange(1, 20)
    assert np.array_equal(j[grid["transition_weights"][:, 1] < 0], np.arange(13, 20))
    # Ordinary exercise uses nonnegative payoff; source replay is explicit opt-in.
    ordinary = source_grid("explicit")
    assert ordinary["values"].min() >= 0
    assert ordinary["continuation"].min() < 0
    assert not ordinary["weights_nonnegative"]


def test_display_rounded_control_price_is_separate_from_unrounded_price():
    result = numerical.fd_control_variate(50, 50, 0.1, 0.4, 5 / 12, 20, 10, s_max=100, kind="put")
    assert result["american"] == pytest.approx(4.067186, abs=5e-7)
    assert result["european"] == pytest.approx(3.911208, abs=5e-7)
    assert result["analytic"] == pytest.approx(4.075981, abs=5e-7)
    assert result["corrected"] == pytest.approx(4.231959, abs=1e-6)
    assert sum(
        round(result[key], 2) * sign
        for key, sign in [("american", 1), ("analytic", 1), ("european", -1)]
    ) == pytest.approx(4.24, abs=1e-12)


def test_european_boundary_and_dense_spatial_derivative_solve():
    grid = source_grid(american=False)
    ds, dt = 5, (5 / 12) / 10
    stock = grid["stock"]
    basis = np.eye(21)
    # Construct differentiation matrices from centered differences of basis functions.
    first = (basis[2:] - basis[:-2]) / (2 * ds)
    second = (basis[2:] - 2 * basis[1:-1] + basis[:-2]) / ds**2
    operator = 0.1 * stock[1:-1, None] * first + 0.4**2 * stock[1:-1, None] ** 2 * second / 2
    operator -= 0.1 * basis[1:-1]
    matrix = np.eye(19) - dt * operator[:, 1:-1]
    value = np.maximum(50 - stock, 0)
    for step in range(1, 11):
        low = 50 * math.exp(-0.1 * step * dt)
        rhs = value[1:-1] + dt * operator[:, 0] * low
        value = np.r_[low, np.linalg.solve(matrix, rhs), 0]
        assert grid["values"][10 - step] == pytest.approx(value, abs=1e-11)
    assert grid["values"][:, 0] == pytest.approx(
        50 * np.exp(-0.1 * (5 / 12 - grid["times"])), abs=1e-12
    )
    assert source_grid()["values"][:, 0] == pytest.approx(50, abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("method", ["implicit", "explicit", "cn", "hopscotch"])
def test_four_schemes_converge_to_independent_payoff_integral(method, kind):
    grid = numerical.fd_grid(
        100,
        100,
        0.04,
        0.25,
        0.75,
        160,
        4000,
        s_max=400,
        method=method,
        kind=kind,
        yield_rate=0.02,
    )
    expected = independent_payoff_integral(100, 100, 0.04, 0.25, 0.75, 0.02, kind)
    assert grid["price"] == pytest.approx(expected, abs=0.015)
    assert grid["values"].min() >= -1e-10
    assert grid["weights_nonnegative"]


def test_american_put_cn_refinement_agrees_with_independent_stopping_tree():
    coarse = numerical.fd_grid(
        50, 50, 0.1, 0.4, 5 / 12, 100, 200, s_max=200, kind="put", american=True, method="cn"
    )
    fine = numerical.fd_grid(
        50, 50, 0.1, 0.4, 5 / 12, 400, 1600, s_max=200, kind="put", american=True, method="cn"
    )
    expected = trees.crr_lattice(50, 50, 0.1, 0.4, 5 / 12, 1600, kind="put", american=True)["price"]
    assert abs(fine["price"] - expected) < abs(coarse["price"] - expected)
    assert fine["price"] == pytest.approx(expected, abs=0.003)
    assert np.all(fine["values"] >= np.maximum(50 - fine["stock"], 0) - 1e-12)


def test_log_explicit_stencil_is_trinomial_with_rational_discount():
    steps, vol, maturity, rate, q = 6, 0.3, 0.6, 0.04, 0.02
    dt = maturity / steps
    dx = vol * math.sqrt(3 * dt)
    grid = numerical.fd_grid(
        100,
        100,
        rate,
        vol,
        maturity,
        2 * steps,
        steps,
        s_min=100 * math.exp(-steps * dx),
        s_max=100 * math.exp(steps * dx),
        space="log",
        method="explicit",
        yield_rate=q,
    )
    reference = trees.trinomial_lattice(100, 100, rate, vol, maturity, steps, yield_rate=q)
    assert grid["price"] == pytest.approx(
        reference["price"] * (math.exp(rate * dt) / (1 + rate * dt)) ** steps, abs=1e-11
    )
    assert grid["transition_weights"].sum(axis=1) == pytest.approx(1, abs=1e-12)
    assert grid["weights_nonnegative"]
    assert grid["transition_weights"][:, 1] == pytest.approx(2 / 3, abs=1e-12)


def test_space_time_and_domain_refinement_are_distinct():
    expected = independent_payoff_integral(100, 100, 0.04, 0.35, 1, 0.02, "call")

    def make(m, n, high):
        return numerical.fd_grid(100, 100, 0.04, 0.35, 1, m, n, s_max=high, yield_rate=0.02)

    space_coarse, space_fine = make(80, 1600, 400), make(320, 1600, 400)
    time_coarse, time_fine = make(320, 20, 400), space_fine
    domain_coarse, domain_fine = make(100, 1600, 125), make(320, 1600, 400)
    for coarse, fine in [
        (space_coarse, space_fine),
        (time_coarse, time_fine),
        (domain_coarse, domain_fine),
    ]:
        assert abs(fine["price"] - expected) < abs(coarse["price"] - expected)
    assert space_fine["price"] == pytest.approx(expected, abs=0.008)


@pytest.mark.parametrize("space", ["spot", "log"])
def test_grid_greeks_and_fixed_grid_vega_agree_with_analytic_values(space):
    kwargs = dict(s_max=400, method="cn", kind="put", yield_rate=0.02, space=space)
    if space == "log":
        kwargs["s_min"] = 25
    grid = numerical.fd_grid(100, 100, 0.04, 0.25, 0.75, 400, 1600, **kwargs)
    node = 100 if space == "spot" else 200
    greeks = numerical.grid_greeks(grid, node)
    assert greeks["stock"] == pytest.approx(100, abs=1e-11)
    assert greeks["delta"] == pytest.approx(
        bsm.put_delta(100, 100, 0.04, 0.25, 0.75, 0.02), abs=3e-4
    )
    assert greeks["gamma"] == pytest.approx(bsm.gamma(100, 100, 0.04, 0.25, 0.75, 0.02), abs=3e-5)
    assert greeks["theta"] == pytest.approx(
        bsm.put_theta(100, 100, 0.04, 0.25, 0.75, 0.02), abs=0.008
    )
    bumped = numerical.fd_vega(100, 100, 0.04, 0.25, 0.75, 400, 1600, bump=1e-4, **kwargs)
    assert bumped["vega"] == pytest.approx(bsm.vega(100, 100, 0.04, 0.25, 0.75, 0.02), abs=0.025)
    assert bumped["vega_per_point"] == pytest.approx(bumped["vega"] / 100, abs=1e-12)
    assert bumped["base"]["stock"] == pytest.approx(bumped["bumped"]["stock"], abs=1e-12)


def test_mathematically_invalid_grid_and_greek_node():
    with pytest.raises(ValueError, match="maturity"):
        numerical.fd_grid(50, 50, 0.1, 0.4, -1, 20, 10, s_max=100)
    with pytest.raises(ValueError, match="log"):
        numerical.fd_grid(50, 50, 0.1, 0.4, 1, 20, 10, s_max=100, s_min=0, space="log")
    with pytest.raises(ValueError, match="discount"):
        numerical.fd_grid(50, 50, -10, 0.4, 1, 20, 10, s_max=100, method="explicit")
    with pytest.raises(ValueError, match="interior"):
        numerical.grid_greeks(source_grid(), 0)


def test_explicit_table_rounding_boundaries_match_rounded_source_maturity():
    exact = source_grid("explicit", obstacle="source")
    assert exact["values"][0, 15] == pytest.approx(0.4549594686238547, abs=1e-12)
    assert exact["values"][2, 12] == pytest.approx(1.1649531447369912, abs=1e-12)
    rounded = numerical.fd_grid(
        50,
        50,
        0.1,
        0.4,
        0.4167,
        20,
        10,
        s_max=100,
        method="explicit",
        kind="put",
        american=True,
        obstacle="source",
    )
    printed = np.vstack((EXPLICIT_TOP, LOWER_ROWS))
    assert rounded["values"].T[::-1] == pytest.approx(printed, abs=0.005)
    # T=.4167 explains the two cells; it does not establish the author's convention.


@pytest.mark.parametrize("method", ["explicit", "hopscotch"])
def test_stable_explicit_and_hopscotch_american_exercise_matches_stopping_tree(method):
    grid = numerical.fd_grid(
        50,
        50,
        0.1,
        0.4,
        5 / 12,
        200,
        4000,
        s_max=200,
        kind="put",
        american=True,
        method=method,
    )
    tree = trees.crr_lattice(50, 50, 0.1, 0.4, 5 / 12, 1600, kind="put", american=True)
    assert grid["weights_nonnegative"]
    assert grid["price"] == pytest.approx(tree["price"], abs=0.008)
    assert np.all(grid["values"] >= np.maximum(50 - grid["stock"], 0) - 1e-12)


def independent_european_put(scheme, spot=50, strike=50, rate=0.1, vol=0.4, maturity=5 / 12, m=20, n=10, s_max=100):
    # Dense matrices and a node loop, sharing only Hull's spot-grid coefficients.
    dt, j = maturity / n, np.arange(m + 1)
    a = 0.5 * vol**2 * j**2 - 0.5 * rate * j
    c = 0.5 * vol**2 * j**2 + 0.5 * rate * j
    b = -(vol**2) * j**2
    operator = np.zeros((m + 1, m + 1))
    for k in range(1, m):
        operator[k, k - 1 : k + 2] = a[k], b[k] - rate, c[k]
    value = np.maximum(strike - j * s_max / m, 0.0)
    for i in range(n - 1, -1, -1):
        low = strike * math.exp(-rate * (n - i) * dt)
        if scheme == "cn":
            left = np.eye(m + 1) - 0.5 * dt * operator
            rhs = (np.eye(m + 1) + 0.5 * dt * operator) @ value
            left[0], left[m] = np.eye(m + 1)[0], np.eye(m + 1)[m]
            rhs[0], rhs[m] = low, 0.0
            value = np.linalg.solve(left, rhs)
            continue
        new = np.empty(m + 1)
        new[0], new[m] = low, 0.0
        for k in range(1, m):
            if (i + k) % 2 == 0:
                new[k] = (dt * a[k] * value[k - 1] + (1 + dt * b[k]) * value[k] + dt * c[k] * value[k + 1]) / (1 + rate * dt)
        for k in range(1, m):
            if (i + k) % 2 == 1:
                new[k] = (value[k] + dt * a[k] * new[k - 1] + dt * c[k] * new[k + 1]) / (1 - dt * (b[k] - rate))
        value = new
    return float(np.interp(spot, j * s_max / m, value))


@pytest.mark.parametrize("method,other", [("cn", "implicit"), ("hopscotch", "explicit")])
def test_cn_and_hopscotch_match_independent_schemes_on_the_source_grid(method, other):
    def price(name):
        return numerical.fd_grid(50, 50, 0.1, 0.4, 5 / 12, 20, 10, s_max=100, method=name, kind="put")["price"]

    assert price(method) == pytest.approx(independent_european_put(method), abs=1e-10)
    assert abs(price(method) - price(other)) > 0.03
