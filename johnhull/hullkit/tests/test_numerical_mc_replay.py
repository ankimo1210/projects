"""Hull21.6: source sample replay and independent probabilistic checks."""

import math
from itertools import product

import numpy as np
import pytest
from hullkit import _numerical_mc as numerical
from hullkit import bsm
from numpy.polynomial.hermite import hermgauss

SOURCE_MOVES = [
    "UUUUD",
    "UUUDD",
    "DDDUU",
    "UUUUU",
    "UUDDU",
    "UDUUD",
    "DDUDD",
    "UUDDU",
    "UUUDU",
    "DDUUD",
]


def test_example_21_7_pi_standard_error_and_interval_from_quoted_stats():
    result = numerical.summary_from_stats(3.04, 1.69, 100)
    assert result["standard_error"] == pytest.approx(0.169, abs=1e-12)
    assert result["confidence95"] == pytest.approx([2.70876, 3.37124], abs=1e-12)


def test_example_21_8_raw_and_prior_rounded_standard_error_conventions():
    raw = numerical.summary_from_stats(4.98, 7.68, 1000)
    display = numerical.summary_from_stats(4.98, 7.68, 1000, interval_se_digits=2)
    assert raw["confidence95"] == pytest.approx([4.503988668, 5.456011332], abs=1e-9)
    assert display["confidence95"] == pytest.approx([4.5096, 5.4504], abs=1e-12)
    assert display["standard_error"] == pytest.approx(7.68 / math.sqrt(1000), abs=1e-12)


def test_table_21_1_visible_dart_rows_and_fixed_seed_pi():
    visible = numerical.pi_from_points(
        [[0.207, 0.690], [0.271, 0.520], [0.007, 0.221], [0.198, 0.403]]
    )
    assert visible["samples"] == pytest.approx([4, 4, 0, 4], abs=1e-12)
    points = np.random.default_rng(21601).random((100000, 2))
    result = numerical.pi_from_points(points)
    assert abs(result["estimate"] - math.pi) < 6 * result["standard_error"]


def test_table_21_2_visible_terminal_quotes_and_discounted_payoffs():
    terminal = np.array([45.95, 54.49, 50.09, 47.46, 44.93, 68.27])
    z = (np.log(terminal / 50) - (0.05 - 0.3**2 / 2) * 0.5) / (0.3 * math.sqrt(0.5))
    result = numerical.european_mc_from_normals(50, 50, 0.05, 0.3, 0.5, z[:, None])
    assert result["discounted_payoffs"] == pytest.approx([0, 4.38, 0.09, 0, 0, 17.82], abs=0.005)


def test_table_21_3_all_ten_averages_payoffs_and_price():
    paths = numerical.tree_sample_paths(50, 0.4, 5 / 12, SOURCE_MOVES)
    result = numerical.arithmetic_asian_details(paths, 50, 0.1, 5 / 12)
    assert result["averages"] == pytest.approx(
        [64.98, 59.82, 42.31, 68.04, 55.22, 55.22, 42.31, 55.22, 62.25, 45.56], abs=0.005
    )
    assert result["payoffs"] == pytest.approx(
        [14.98, 9.82, 0, 18.04, 5.22, 5.22, 0, 5.22, 12.25, 0], abs=0.005
    )
    assert result["payoffs"].mean() == pytest.approx(7.07582, abs=0.00001)
    assert result["price"] == pytest.approx(6.78705, abs=0.00001)


def test_asian_all_thirty_two_paths_independent_incremental_integral():
    moves = ["".join(x) for x in product("UD", repeat=5)]
    paths = numerical.tree_sample_paths(50, 0.4, 5 / 12, moves)
    result = numerical.arithmetic_asian_details(paths, 50, 0.1, 5 / 12)
    u = math.exp(0.4 * math.sqrt(1 / 12))
    p = (math.exp(0.1 / 12) - 1 / u) / (u - 1 / u)
    weights = np.array([p ** m.count("U") * (1 - p) ** m.count("D") for m in moves])
    independent = 0
    for path, weight in zip(moves, weights, strict=True):
        current, total = 50.0, 50.0
        for move in path:
            current *= u if move == "U" else 1 / u
            total += current
        independent += weight * max(total / 6 - 50, 0) * math.exp(-0.1 * 5 / 12)
    assert np.dot(weights, result["discounted_payoffs"]) == pytest.approx(independent, abs=1e-11)


@pytest.mark.parametrize("scheme", ["exact", "euler"])
def test_replayed_one_step_moments_independent_gauss_hermite(scheme):
    nodes, weights = hermgauss(40)
    z = (math.sqrt(2) * nodes)[:, None]
    terminal = numerical.gbm_paths_from_normals(
        50, 0.05, 0.3, 0.5, z, yield_rate=0.02, scheme=scheme
    )[:, -1]
    w = weights / math.sqrt(math.pi)
    mean = np.dot(w, terminal)
    second = np.dot(w, terminal**2)
    if scheme == "exact":
        expected_mean = 50 * math.exp(0.03 * 0.5)
        expected_second = 50**2 * math.exp((2 * 0.03 + 0.3**2) * 0.5)
    else:
        expected_mean = 50 * (1 + 0.03 * 0.5)
        expected_second = 50**2 * ((1 + 0.03 * 0.5) ** 2 + 0.3**2 * 0.5)
    assert mean == pytest.approx(expected_mean, abs=1e-11)
    assert second == pytest.approx(expected_second, abs=1e-9)


def test_euler_can_go_negative_without_clipping():
    paths = numerical.gbm_paths_from_normals(50, 0, 1, 1, [[-4], [0]], scheme="euler")
    assert paths[0, -1] == pytest.approx(-150, abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_fixed_seed_mc_table_21_2_bsm_with_discounted_se(kind):
    z = np.random.default_rng(21602).standard_normal((120000, 1))
    result = numerical.european_mc_from_normals(50, 50, 0.05, 0.3, 0.5, z, kind=kind)
    exact = (bsm.call_price if kind == "call" else bsm.put_price)(50, 50, 0.05, 0.3, 0.5)
    if kind == "call":
        assert exact == pytest.approx(4.817, abs=0.0005)
    assert abs(result["price"] - exact) < 6 * result["standard_error"]
    assert result["standard_error"] == pytest.approx(
        np.std(result["discounted_payoffs"], ddof=1) / math.sqrt(120000), abs=1e-12
    )


def test_cholesky_multifactor_covariance_and_singular_valid_correlation():
    correlation = np.array([[1, 0.6, 0.2], [0.6, 1, 0.1], [0.2, 0.1, 1]])
    z = np.random.default_rng(21603).standard_normal((100000, 3))
    result = numerical.correlate_normals(z, correlation)
    covariance = np.cov(result["normals"], rowvar=False)
    covariance_se = np.sqrt((1 + correlation**2) / 100000)
    assert np.all(np.abs(covariance - correlation) < 6 * covariance_se)
    assert result["factor"] @ result["factor"].T == pytest.approx(correlation, abs=1e-12)
    singular = numerical.correlate_normals(z[:, :2], [[1, -1], [-1, 1]])
    assert singular["normals"][:, 0] == pytest.approx(-singular["normals"][:, 1], abs=1e-12)


@pytest.mark.parametrize(
    "parameter,bump,exact",
    [
        ("spot", 0.005, float(bsm.call_delta(50, 50, 0.05, 0.3, 0.5))),
        ("sigma", 0.0001, float(bsm.vega(50, 50, 0.05, 0.3, 0.5))),
        ("rate", 0.0001, float(bsm.call_rho(50, 50, 0.05, 0.3, 0.5))),
    ],
)
def test_common_random_greeks_against_independent_analytic_values(parameter, bump, exact):
    z = np.random.default_rng(21604).standard_normal((100000, 1))
    result = numerical.common_random_greek(
        50, 50, 0.05, 0.3, 0.5, z, parameter=parameter, bump=bump
    )
    assert abs(result["estimate"] - exact) < 6 * result["standard_error"] + 0.002
    assert result["standard_error"] == pytest.approx(
        np.std(result["samples"], ddof=1) / math.sqrt(len(z)), abs=1e-12
    )


def test_paired_greek_uses_difference_samples_and_reduces_noise():
    rng = np.random.default_rng(21605)
    z = rng.standard_normal((20000, 1))
    paired = numerical.common_random_greek(50, 50, 0.05, 0.3, 0.5, z, parameter="spot", bump=0.005)
    original = numerical.european_mc_from_normals(50, 50, 0.05, 0.3, 0.5, z)["discounted_payoffs"]
    unrelated = numerical.european_mc_from_normals(
        50.005, 50, 0.05, 0.3, 0.5, rng.standard_normal(z.shape)
    )["discounted_payoffs"]
    unpaired_se = np.std((unrelated - original) / 0.005, ddof=1) / math.sqrt(len(z))
    assert paired["standard_error"] < unpaired_se / 10


def test_mathematically_invalid_correlation_and_insufficient_se_sample():
    with pytest.raises(ValueError):
        numerical.correlate_normals(np.zeros((3, 2)), [[1, 1.2], [1.2, 1]])
    with pytest.raises(ValueError):
        numerical.iid_summary([1])
