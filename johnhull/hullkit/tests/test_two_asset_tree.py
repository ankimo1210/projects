"""Hull GE §27.7 options on two correlated assets: three 3-D tree constructions."""

import functools
import math

import numpy as np
import pytest
from hullkit.exotics import exchange_option
from hullkit.two_asset_tree import two_asset_lattice, two_asset_tree

MARKET = dict(
    rate=0.05,
    volatilities=(0.20, 0.30),
    correlation=0.5,
    dividend_yields=(0.06, 0.02),
)
SPOTS = (100.0, 100.0)
METHODS = ("transform", "rubinstein", "adjusted")
# Stulz (1982) call on the maximum, K = 100, from the independent reference
# (scripts/build_two_asset_reference.py integrates the payoff conditional on S1).
MAX_CALL = 15.926819308643
# American exchange option max(S1 - S2, 0): the one-dimensional reduction
# (S2 x an American call on S1/S2, struck at 1, rate q2 and yield q1),
# solved by CRR and Crank-Nicolson in the independent reference.
AMERICAN_EXCHANGE = 8.76368


def _exchange(s1, s2):
    return np.maximum(s1 - s2, 0.0)


def _max_call(s1, s2):
    return np.maximum(np.maximum(s1, s2) - 100.0, 0.0)


def _margrabe():
    return exchange_option(100.0, 100.0, 0.30, 0.20, 0.5, 1.0, q_u=0.02, q_v=0.06)


def _alternative_binomial(spot, strike, rate, dividend, volatility, maturity, steps, american):
    """Hull §21.4 alternative binomial call: probabilities 0.5, drift in the moves."""
    dt = maturity / steps
    drift = (rate - dividend - volatility**2 / 2) * dt
    shock = volatility * math.sqrt(dt)
    discount = math.exp(-rate * dt)

    def stock(step):
        ups = np.arange(step + 1)
        return spot * np.exp(step * drift + (2 * ups - step) * shock)

    values = np.maximum(stock(steps) - strike, 0.0)
    for step in range(steps - 1, -1, -1):
        values = discount * 0.5 * (values[1:] + values[:-1])
        if american:
            values = np.maximum(values, stock(step) - strike)
    return float(values[0])


def test_uncorrelated_trees_combine_with_product_probabilities():
    for method in METHODS:
        p_uu, p_ud, p_du, p_dd = two_asset_lattice(
            0.05, (0.20, 0.30), 0.0, 0.01, method=method, dividend_yields=(0.06, 0.02)
        ).probabilities
        assert p_uu + p_ud + p_du + p_dd == pytest.approx(1.0, abs=1e-15)
        assert p_uu * p_dd == pytest.approx(p_ud * p_du, abs=1e-15)


def test_adjusted_probabilities_reproduce_tables_27_2_and_27_3():
    uncorrelated = two_asset_lattice(0.05, (0.2, 0.3), 0.0, 0.01, method="adjusted")
    assert uncorrelated.probabilities == (0.25, 0.25, 0.25, 0.25)
    for rho in (-1.0, -0.4, 0.5, 1.0):
        lattice = two_asset_lattice(0.05, (0.2, 0.3), rho, 0.01, method="adjusted")
        same, opposite = 0.25 * (1 + rho), 0.25 * (1 - rho)
        assert lattice.probabilities == pytest.approx((same, opposite, opposite, same), abs=1e-15)


def test_rubinstein_branches_are_hulls_u1_d1_and_a_to_d():
    rate, (q1, q2), (s1, s2), rho, dt = 0.05, (0.06, 0.02), (0.20, 0.30), 0.5, 0.04
    lattice = two_asset_lattice(
        rate, (s1, s2), rho, dt, method="rubinstein", dividend_yields=(q1, q2)
    )
    root = math.sqrt(dt)
    orthogonal = math.sqrt(1 - rho**2)
    m1 = (rate - q1 - s1**2 / 2) * dt
    m2 = (rate - q2 - s2**2 / 2) * dt
    u1, d1 = m1 + s1 * root, m1 - s1 * root
    a = m2 + s2 * root * (rho + orthogonal)
    b = m2 + s2 * root * (rho - orthogonal)
    c = m2 - s2 * root * (rho - orthogonal)
    d = m2 - s2 * root * (rho + orthogonal)
    moves, probabilities = zip(*lattice.branches(), strict=True)
    assert np.allclose(moves, [(u1, a), (u1, b), (d1, c), (d1, d)], rtol=0, atol=1e-15)
    assert probabilities == (0.25, 0.25, 0.25, 0.25)


def test_transform_branches_move_x1_and_x2_by_plus_or_minus_h():
    rate, (q1, q2), (s1, s2), rho, dt = 0.05, (0.06, 0.02), (0.20, 0.30), 0.5, 0.04
    lattice = two_asset_lattice(
        rate, (s1, s2), rho, dt, method="transform", dividend_yields=(q1, q2)
    )
    m1 = (rate - q1 - s1**2 / 2) * dt
    m2 = (rate - q2 - s2**2 / 2) * dt
    mean_1, mean_2 = s2 * m1 + s1 * m2, s2 * m1 - s1 * m2
    var_1, var_2 = 2 * (1 + rho) * (s1 * s2) ** 2 * dt, 2 * (1 - rho) * (s1 * s2) ** 2 * dt
    h1, h2 = math.sqrt(var_1 + mean_1**2), math.sqrt(var_2 + mean_2**2)
    p1, p2 = 0.5 + mean_1 / (2 * h1), 0.5 + mean_2 / (2 * h2)
    moves, probabilities = zip(*lattice.branches(), strict=True)
    x1 = [s2 * l1 + s1 * l2 for l1, l2 in moves]
    x2 = [s2 * l1 - s1 * l2 for l1, l2 in moves]
    assert np.allclose(x1, [h1, h1, -h1, -h1], rtol=0, atol=1e-15)
    assert np.allclose(x2, [h2, -h2, h2, -h2], rtol=0, atol=1e-15)
    expected = (p1 * p2, p1 * (1 - p2), (1 - p1) * p2, (1 - p1) * (1 - p2))
    assert probabilities == pytest.approx(expected, abs=1e-15)
    # Inverse relationships S1 = exp[(x1 + x2) / (2 sigma2)], S2 = exp[(x1 - x2) / (2 sigma1)].
    for (l1, l2), a, b in zip(moves, x1, x2, strict=True):
        assert l1 == pytest.approx((a + b) / (2 * s2), abs=1e-15)
        assert l2 == pytest.approx((a - b) / (2 * s1), abs=1e-15)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("rho", [-1.0, -0.3, 0.0, 0.5, 1.0])
def test_one_step_log_moments_are_exact(method, rho):
    rate, dividends, (s1, s2), dt = 0.05, (0.06, 0.02), (0.20, 0.30), 0.04
    lattice = two_asset_lattice(rate, (s1, s2), rho, dt, method=method, dividend_yields=dividends)
    mean, covariance = lattice.log_moments()
    expected_mean = [(rate - q - s**2 / 2) * dt for q, s in zip(dividends, (s1, s2), strict=True)]
    expected = np.array([[s1**2, rho * s1 * s2], [rho * s1 * s2, s2**2]]) * dt
    assert np.allclose(mean, expected_mean, rtol=0, atol=1e-16)
    assert np.allclose(covariance, expected, rtol=0, atol=1e-16)


@pytest.mark.parametrize("rho", [-1.0, 0.0, 1.0])
@pytest.mark.parametrize("exercise", ["european", "american"])
def test_rubinstein_and_adjusted_coincide_at_zero_and_perfect_correlation(rho, exercise):
    market = dict(MARKET, correlation=rho)
    prices = [
        two_asset_tree(
            SPOTS, _max_call, **market, maturity=1.0, steps=60, method=method, exercise=exercise
        ).price
        for method in ("rubinstein", "adjusted")
    ]
    assert prices[0] == pytest.approx(prices[1], abs=1e-12)


@pytest.mark.parametrize("method", ["rubinstein", "adjusted"])
@pytest.mark.parametrize("american", [False, True])
def test_first_asset_marginal_is_the_alternative_binomial_tree(method, american):
    exercise = "american" if american else "european"
    tree = two_asset_tree(
        SPOTS,
        lambda s1, s2: np.maximum(s1 - 95.0, 0.0),
        **MARKET,
        maturity=1.0,
        steps=80,
        method=method,
        exercise=exercise,
    )
    expected = _alternative_binomial(100.0, 95.0, 0.05, 0.06, 0.20, 1.0, 80, american)
    assert tree.price == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("american", [False, True])
def test_adjusted_second_asset_marginal_is_the_alternative_binomial_tree(american):
    exercise = "american" if american else "european"
    tree = two_asset_tree(
        SPOTS,
        lambda s1, s2: np.maximum(s2 - 105.0, 0.0),
        **MARKET,
        maturity=1.0,
        steps=80,
        method="adjusted",
        exercise=exercise,
    )
    expected = _alternative_binomial(100.0, 105.0, 0.05, 0.02, 0.30, 1.0, 80, american)
    assert tree.price == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("method", METHODS)
def test_european_exchange_converges_to_margrabe(method):
    price = two_asset_tree(SPOTS, _exchange, **MARKET, maturity=1.0, steps=400, method=method).price
    assert abs(price - _margrabe()) < 2.5e-3


def test_transform_tree_converges_at_first_order_in_the_example():
    errors = [
        two_asset_tree(SPOTS, _max_call, **MARKET, maturity=1.0, steps=n, method="transform").price
        - MAX_CALL
        for n in (100, 200, 400)
    ]
    assert all(error > 0 for error in errors)
    assert errors[1] / errors[0] == pytest.approx(0.5, abs=0.05)
    assert errors[2] / errors[1] == pytest.approx(0.5, abs=0.05)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("steps", [400, 401])
def test_american_exchange_matches_the_one_dimensional_reduction(method, steps):
    tree = two_asset_tree(
        SPOTS, _exchange, **MARKET, maturity=1.0, steps=steps, method=method, exercise="american"
    )
    assert abs(tree.price - AMERICAN_EXCHANGE) < 3e-3
    assert tree.price > _margrabe() + 0.4


def _recursive_american(spots, payoff, lattice, rate, steps):
    """Plain recursion over the four branches, exercising at every node."""
    moves = lattice.branches()
    discount = math.exp(-rate * lattice.dt)

    @functools.cache
    def value(step, j, k):
        logs = [
            math.log(spot) + step * d + j * a + k * b
            for spot, d, a, b in zip(
                spots, lattice.drift, lattice.j_move, lattice.k_move, strict=True
            )
        ]
        exercise = float(payoff(np.array(math.exp(logs[0])), np.array(math.exp(logs[1]))))
        if step == steps:
            return exercise
        held = discount * sum(
            probability * value(step + 1, j + dj, k + dk)
            for ((dj, dk), (_, probability)) in zip(
                ((1, 1), (1, -1), (-1, 1), (-1, -1)), moves, strict=True
            )
        )
        return max(held, exercise)

    return value(0, 0, 0)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("spots", [(120.0, 100.0), (100.0, 100.0)])
def test_american_exercise_is_checked_from_the_first_step(method, spots):
    # q1 = 25%: at (120, 100) exercise is optimal at once; at (100, 100) it binds
    # at steps 1 and 2 but not at step 0, so each early step must be exercised.
    market = dict(MARKET, dividend_yields=(0.25, 0.0))
    tree = two_asset_tree(
        spots, _exchange, **market, maturity=1.0, steps=6, method=method, exercise="american"
    )
    lattice = two_asset_lattice(
        0.05, (0.20, 0.30), 0.5, 1.0 / 6, method=method, dividend_yields=(0.25, 0.0)
    )
    assert tree.price == pytest.approx(
        _recursive_american(spots, _exchange, lattice, 0.05, 6), abs=1e-12
    )
    if spots == (120.0, 100.0):
        assert tree.price == pytest.approx(20.0, abs=1e-9)


@pytest.mark.parametrize("method", METHODS)
def test_american_value_dominates_european_and_intrinsic(method):
    arguments = dict(MARKET, maturity=1.0, steps=50, method=method)
    european = two_asset_tree((110.0, 90.0), _max_call, **arguments).price
    american = two_asset_tree((110.0, 90.0), _max_call, **arguments, exercise="american").price
    assert american >= european - 1e-12
    assert american >= 10.0


def test_transform_survives_a_deterministic_second_variable():
    # rho = 1 gives x2 no volatility; choosing sigma2 m1 = sigma1 m2 also removes its drift.
    lattice = two_asset_lattice(0.05, (0.2, 0.2), 1.0, 0.01, method="transform")
    assert all(math.isfinite(p) and 0.0 <= p <= 1.0 for p in lattice.probabilities)
    tree = two_asset_tree(SPOTS, _exchange, 0.05, (0.2, 0.2), 1.0, 1.0, 40, method="transform")
    assert tree.price == pytest.approx(0.0, abs=1e-12)


def test_result_reports_the_lattice_used():
    tree = two_asset_tree(
        SPOTS, _exchange, **MARKET, maturity=1.0, steps=10, method="rubinstein", exercise="american"
    )
    assert (tree.method, tree.exercise, tree.steps) == ("rubinstein", "american", 10)
    assert tree.lattice.dt == pytest.approx(0.1)
    assert tree.lattice.method == "rubinstein"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (dict(spots=(0.0, 100.0)), "spots"),
        (dict(spots=(100.0, math.nan)), "finite"),
        (dict(volatilities=(0.2, 0.0)), "volatilities"),
        (dict(volatilities=(0.2,)), "two"),
        (dict(correlation=1.01), "correlation"),
        (dict(correlation=math.nan), "finite"),
        (dict(maturity=0.0), "maturity"),
        (dict(steps=0), "steps"),
        (dict(steps=10.0), "steps"),
        (dict(steps=True), "steps"),
        (dict(method="cholesky"), "method"),
        (dict(exercise="bermudan"), "exercise"),
        (dict(dividend_yields=(0.0, math.inf)), "finite"),
        (dict(rate=math.nan), "finite"),
        (dict(payoff=None), "payoff"),
        (dict(payoff=lambda s1, s2: 1.0), "shape"),
        (dict(payoff=lambda s1, s2: np.full_like(s1, np.nan)), "finite"),
    ],
)
def test_invalid_inputs_are_rejected(change, message):
    arguments = dict(
        spots=SPOTS,
        payoff=_exchange,
        **MARKET,
        maturity=1.0,
        steps=10,
        method="adjusted",
        exercise="european",
    )
    arguments.update(change)
    with pytest.raises(ValueError, match=message):
        two_asset_tree(**arguments)


def test_lattice_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="dt"):
        two_asset_lattice(0.05, (0.2, 0.3), 0.5, 0.0)
    with pytest.raises(ValueError, match="correlation"):
        two_asset_lattice(0.05, (0.2, 0.3), -1.5, 0.01)
    with pytest.raises(ValueError, match="method"):
        two_asset_lattice(0.05, (0.2, 0.3), 0.5, 0.01, method="crr")
