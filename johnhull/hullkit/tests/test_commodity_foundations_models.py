"""Hull GE §35.4 and independent paths/density/generator calculations."""

import math
from functools import lru_cache

import numpy as np
import pytest
from hullkit import _commodity_foundations as c
from scipy.integrate import quad
from scipy.stats import norm


def source_paths():
    """Nonrecombining enumeration with independently written Hull probabilities."""
    spacing = 0.2 * math.sqrt(3)

    def branches(j):
        if j == 2:
            return [(2, 133 / 150), (1, 2 / 75), (0, 13 / 150)]
        if j == -2:
            return [(0, 13 / 150), (-1, 2 / 75), (-2, 133 / 150)]
        return [
            (j + 1, 1 / 6 + (0.01 * j * j - 0.1 * j) / 2),
            (j, 2 / 3 - 0.01 * j * j),
            (j - 1, 1 / 6 + (0.01 * j * j + 0.1 * j) / 2),
        ]

    paths = [[(0, 1.0)]]
    for _ in range(3):
        paths.append([(child, weight * p) for j, weight in paths[-1] for child, p in branches(j)])
    alpha = [math.log(20)]
    for future, layer in zip([22, 23, 24], paths[1:], strict=True):
        alpha.append(math.log(future / sum(w * math.exp(spacing * j) for j, w in layer)))
    return branches, alpha, spacing, paths


def test_source_growth_investment_and_seasonal_values():
    a = c.futures_growth(60.60, 62.70, 1 / 6)
    assert a["log_growth"] == pytest.approx(0.034, rel=0, abs=0.0005)
    assert 100 * a["annual_growth"] == pytest.approx(20.4, rel=0, abs=0.05)
    value = c.commodity_investment(100000, [0.25, 0.5, 0.75], [20000] * 3, 1, 300000, 0.644, 0.1)
    assert value / 1000 == pytest.approx(17.729, rel=0, abs=0.0005)
    terminal_cash = (
        -100000 * math.exp(0.1)
        - sum(20000 * math.exp(0.1 * (1 - t)) for t in [0.25, 0.5, 0.75])
        + 300000 * 0.644
    )
    assert value == pytest.approx(terminal_cash * math.exp(-0.1), abs=1e-8)
    a = c.seasonal_futures([9, 12], [40, 44], [0.95, 1.1], [9, 10, 11, 12], [0.95, 0.85, 0.8, 1.1])
    assert np.r_[a["deseasonalized"], a["interpolated"][1:3], a["futures"][1:3]] == pytest.approx(
        [42.1, 40, 41.4, 40.7, 35.2, 32.6], rel=0, abs=0.05
    )
    for index in [1, 2]:
        weight = index / 3
        direct = (40 / 0.95 * (1 - weight) + 44 / 1.1 * weight) * [0.95, 0.85, 0.8, 1.1][index]
        assert a["futures"][index] == pytest.approx(direct)


def test_source_all_tree_prices_probabilities_and_shifts():
    tree = c.build_commodity_tree(20, [22, 23, 24], 0.1, 0.2)
    levels = tree["levels"]
    assert tree["spacing"] == pytest.approx(0.3464, rel=0, abs=0.00005)
    assert [levels[1]["alpha"], levels[2]["alpha"]] == pytest.approx(
        [3.071, 3.099], rel=0, abs=0.0005
    )
    for layer, printed in zip(
        levels[1:],
        [
            [30.49, 21.56, 15.25],
            [44.35, 31.37, 22.18, 15.69, 11.09],
            [45.68, 32.30, 22.85, 16.16, 11.43],
        ],
        strict=True,
    ):
        assert layer["spot"][::-1] == pytest.approx(printed, rel=0, abs=0.005)
    assert abs(levels[2]["spot"][0] - 11.10) > 0.005
    assert levels[2]["reach_probabilities"][::-1] == pytest.approx(
        [0.0203, 0.2206, 0.5183, 0.2206, 0.0203], rel=0, abs=0.00005
    )
    expected = np.array(
        [
            [0.1667, 0.6666, 0.1667],
            [0.1217, 0.6566, 0.2217],
            [0.1667, 0.6666, 0.1667],
            [0.2217, 0.6566, 0.1217],
            [0.8867, 0.0266, 0.0867],
            [0.1217, 0.6566, 0.2217],
            [0.1667, 0.6666, 0.1667],
            [0.2217, 0.6566, 0.1217],
            [0.0867, 0.0266, 0.8867],
        ]
    )
    actual = np.vstack([layer["probabilities"][::-1, ::-1] for layer in levels[:-1]])
    assert actual[:, [0, 2]] == pytest.approx(expected[:, [0, 2]], rel=0, abs=0.00005)
    assert np.floor(actual[:, 1] * 10000 + 1e-9) / 10000 == pytest.approx(
        expected[:, 1], rel=0, abs=1e-12
    )
    for future, layer in zip([20, 22, 23, 24], levels, strict=True):
        assert layer["reach_probabilities"] @ layer["spot"] == pytest.approx(
            future, rel=0, abs=1e-12
        )
    for i, layer in enumerate(levels[:-1]):
        changes = levels[i + 1]["x"][layer["successors"]] - layer["x"][:, None]
        mean = -0.1 * layer["x"]
        assert np.sum(layer["probabilities"] * changes, axis=1) == pytest.approx(mean, abs=1e-13)
        assert np.sum(
            layer["probabilities"] * (changes - mean[:, None]) ** 2, axis=1
        ) == pytest.approx(np.full(len(mean), 0.04), abs=1e-13)


def test_source_american_put_and_independent_nonrecombining_paths():
    tree = c.build_commodity_tree(20, [22, 23, 24], 0.1, 0.2)
    option = c.commodity_option(tree, 20, 0.03)
    assert option["value"] == pytest.approx(1.501100501, rel=0, abs=5e-10)
    assert abs(option["value"] - 1.48) > 0.005
    assert option["values"][1][::-1] == pytest.approx([0.13, 1.10, 4.75], rel=0, abs=0.005)
    assert option["values"][2][::-1] == pytest.approx([0, 0, 0.62, 4.31, 8.91], rel=0, abs=0.005)
    assert abs(option["values"][2][0] - 8.90) > 0.005
    assert option["values"][3][::-1] == pytest.approx([0, 0, 0, 3.84, 8.57], rel=0, abs=0.005)
    assert np.array_equal(option["exercise"][1], [True, False, False])
    assert np.array_equal(option["exercise"][2], [True, True, False, False, False])
    branches, alpha, spacing, paths = source_paths()

    @lru_cache(None)
    def value(t, j, american):
        payoff = max(20 - math.exp(alpha[t] + spacing * j), 0)
        if t == 3:
            return payoff
        continuation = math.exp(-0.03) * sum(p * value(t + 1, k, american) for k, p in branches(j))
        return max(payoff, continuation) if american else continuation

    for t, layer in enumerate(tree["levels"]):
        assert layer["alpha"] == pytest.approx(alpha[t], abs=1e-13)
        assert option["values"][t] == pytest.approx(
            [value(t, int(j), True) for j in layer["labels"]], abs=1e-12
        )
    european = c.commodity_option(tree, 20, 0.03, american=False)
    path_value = math.exp(-0.09) * sum(
        w * max(20 - math.exp(alpha[3] + spacing * j), 0) for j, w in paths[-1]
    )
    assert european["value"] == pytest.approx(path_value, abs=1e-12)


def test_independent_continuous_ou_density_and_euler_mesh_convergence():
    law = c.commodity_terminal_law(24, 0.1, 0.2, 3)
    sd = math.sqrt(0.04 * (1 - math.exp(-0.6)) / 0.2)
    mean = math.log(24) - sd * sd / 2
    assert [law["mean_log"], law["variance"]] == pytest.approx([mean, sd * sd], abs=1e-14)
    reference = (
        math.exp(-0.09)
        * quad(
            lambda z: max(20 - math.exp(mean + sd * z), 0) * norm.pdf(z),
            -12,
            (math.log(20) - mean) / sd,
            epsabs=1e-11,
        )[0]
    )
    errors = []
    for steps in [64, 256]:
        times = np.arange(1, steps + 1) * 3 / steps
        futures = np.exp(np.interp(times, [0, 1, 2, 3], np.log([20, 22, 23, 24])))
        tree = c.build_commodity_tree(20, futures, 0.1, 0.2, dt=3 / steps)
        price = c.commodity_option(tree, 20, 0.03, american=False)["value"]
        errors.append(abs(price - reference))
    assert errors[1] < errors[0]
    assert errors[1] < 0.003
    deterministic = c.build_commodity_tree(20, [22, 23], 0.1, 0)
    assert c.commodity_option(deterministic, 24, 0.03, american=False)["value"] == pytest.approx(
        math.exp(-0.06)
    )


def test_independent_jump_expectation_compound_poisson_and_fixed_seed_mc():
    jumps = np.log([1.25, 0.8])
    prob = np.array([0.3, 0.7])
    intensity = 0.5
    T = 2.0
    log_growth = c.log_ou_jump_growth(0, T, intensity, jumps, prob)
    assert log_growth == pytest.approx(intensity * T * (prob @ np.exp(jumps) - 1), abs=1e-13)
    rng = np.random.default_rng(3534)
    count = rng.poisson(intensity * T, 150000)
    up = rng.binomial(count, 0.3)
    growth = np.exp(up * jumps[0] + (count - up) * jumps[1])
    assert abs(growth.mean() - math.exp(log_growth)) <= 6 * growth.std(ddof=1) / math.sqrt(
        len(growth)
    )
    adjusted = c.log_ou_jump_growth(0.2, T, intensity, jumps, prob)
    # For one jump at a uniform random time, reversion attenuates its log size.
    one_jump = (
        quad(
            lambda age: (
                0.3 * math.exp(jumps[0] * math.exp(-0.2 * age))
                + 0.7 * math.exp(jumps[1] * math.exp(-0.2 * age))
            ),
            0,
            T,
        )[0]
        / T
    )
    mixture = sum(
        math.exp(-intensity * T) * (intensity * T) ** n / math.factorial(n) * one_jump**n
        for n in range(20)
    )
    assert math.exp(adjusted) == pytest.approx(mixture, abs=1e-12)


def test_independent_ito_generators_for_convenience_and_variance_models():
    gs = c.convenience_yield_coefficients(0.02, 0.03, 0.4, 0.05, 0.2, 0.1, -0.3)
    assert gs["drift"] == pytest.approx([0.03 - 0.02 - 0.2**2 / 2, 0.4 * (0.05 - 0.02)])
    assert gs["covariance"] == pytest.approx(np.array([[0.04, -0.006], [-0.006, 0.01]]))
    eg = c.stochastic_variance_coefficients(math.log(20), 0.04, 0.1, 3.2, 0.5, 0.06, 0.3, -0.2)
    assert eg["drift"] == pytest.approx(
        [0.1 * (3.2 - math.log(20)) - 0.04 / 2, 0.5 * (0.06 - 0.04)]
    )
    assert eg["covariance"] == pytest.approx(np.array([[0.04, -0.0024], [-0.0024, 0.0036]]))
    for model, source_spot_drift in [(gs, 0.03 - 0.02), (eg, 0.1 * (3.2 - math.log(20)))]:
        # Generator of S=exp(log S) adds half its quadratic variation.
        generator = model["drift"][0] + model["covariance"][0, 0] / 2
        assert generator == pytest.approx(source_spot_drift, abs=1e-14)
        assert np.linalg.eigvalsh(model["covariance"]).min() >= -1e-14
