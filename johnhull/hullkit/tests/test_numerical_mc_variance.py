"""Hull21.7: distinguish statistical units for six variance procedures."""

import math

import numpy as np
import pytest
from hullkit import _numerical_mc as numerical
from hullkit import bsm
from scipy.integrate import quad
from scipy.stats import norm


@pytest.mark.parametrize("kind", ["call", "put"])
def test_antithetic_pair_se_and_same_cost_plain_mc(kind):
    rng = np.random.default_rng(21701)
    z = rng.standard_normal((20000, 1))
    result = numerical.antithetic_mc(50, 50, 0.05, 0.3, 0.5, z, kind=kind)
    exact = (bsm.call_price if kind == "call" else bsm.put_price)(50, 50, 0.05, 0.3, 0.5)
    assert abs(result["price"] - exact) < 6 * result["standard_error"]
    forward = numerical.european_mc_from_normals(50, 50, 0.05, 0.3, 0.5, z, kind=kind)[
        "discounted_payoffs"
    ]
    reverse = numerical.european_mc_from_normals(50, 50, 0.05, 0.3, 0.5, -z, kind=kind)[
        "discounted_payoffs"
    ]
    pair = (forward + reverse) / 2
    assert result["standard_error"] == pytest.approx(
        np.std(pair, ddof=1) / math.sqrt(20000), abs=1e-12
    )
    assert result["payoff_evaluations"] == 40000
    plain = numerical.european_mc_from_normals(
        50, 50, 0.05, 0.3, 0.5, rng.standard_normal((40000, 1)), kind=kind
    )
    assert result["standard_error"] < plain["standard_error"]


def test_equation_21_20_default_unit_control_against_known_integral():
    z = np.random.default_rng(21702).standard_normal(10000)
    result = numerical.control_adjustment(z * z + 3, z * z, 1)
    assert result["samples"] == pytest.approx(np.full(10000, 4), abs=1e-12)
    assert result["estimate"] == pytest.approx(
        quad(lambda x: (x * x + 3) * norm.pdf(x), -12, 12)[0], abs=1e-11
    )
    assert result["standard_error"] == pytest.approx(0, abs=1e-12)


def test_fixed_control_coefficient_known_discounted_stock_mean():
    z = np.random.default_rng(21703).standard_normal((50000, 1))
    paths = numerical.gbm_paths_from_normals(50, 0.05, 0.3, 0.5, z, yield_rate=0.02)
    payoff = math.exp(-0.05 * 0.5) * np.maximum(paths[:, -1] - 50, 0)
    control = math.exp(-0.05 * 0.5) * paths[:, -1]
    adjusted = numerical.control_adjustment(payoff, control, 50 * math.exp(-0.02 * 0.5), beta=0.6)
    exact = bsm.call_price(50, 50, 0.05, 0.3, 0.5, q=0.02)
    assert abs(adjusted["estimate"] - exact) < 6 * adjusted["standard_error"]
    assert adjusted["standard_error"] < np.std(payoff, ddof=1) / math.sqrt(len(z))


def test_source_tail_conditioned_sampling_against_independent_q_payoff_integral():
    uniform = np.random.default_rng(21704).random(20000)
    result = numerical.conditional_call_from_uniforms(
        100, 150, 0.03, 0.2, 0.5, uniform, yield_rate=0.01
    )
    width = 0.2 * math.sqrt(0.5)
    mean = math.log(100) + (0.03 - 0.01 - 0.2**2 / 2) * 0.5
    cutoff = (math.log(150) - mean) / width
    exact = (
        math.exp(-0.03 * 0.5)
        * quad(
            lambda z: (math.exp(mean + width * z) - 150) * norm.pdf(z), cutoff, 12, epsabs=1e-13
        )[0]
    )
    assert abs(result["price"] - exact) < 6 * result["standard_error"]
    assert result["tail_probability"] == pytest.approx(
        quad(norm.pdf, cutoff, 12, epsabs=1e-13)[0], abs=1e-12
    )
    assert np.all(result["terminal_stock"] > 150)
    assert result["samples"] == pytest.approx(
        result["tail_probability"] * math.exp(-0.03 * 0.5) * (result["terminal_stock"] - 150),
        abs=1e-12,
    )


def test_textbook_four_median_strata_against_integrated_normal_cdf():
    z = numerical.stratified_normal(4)
    assert z == pytest.approx([-1.150349380, -0.318639364, 0.318639364, 1.150349380], abs=1e-9)
    probabilities = [quad(norm.pdf, -12, x, epsabs=1e-13)[0] for x in z]
    assert probabilities == pytest.approx([0.125, 0.375, 0.625, 0.875], abs=1e-12)


def test_randomized_stratification_se_uses_independent_batches():
    rng = np.random.default_rng(21705)
    batch = []
    for _ in range(32):
        z = numerical.stratified_normal(256, uniforms=rng.random(256))
        terminal = 50 * np.exp((0.05 - 0.3**2 / 2) * 0.5 + 0.3 * math.sqrt(0.5) * z)
        batch.append(float(math.exp(-0.05 * 0.5) * np.maximum(terminal - 50, 0).mean()))
    summary = numerical.iid_summary(batch)
    assert (
        abs(summary["estimate"] - bsm.call_price(50, 50, 0.05, 0.3, 0.5))
        < 6 * summary["standard_error"]
    )


def test_moment_matching_sample_std_convention_and_dependent_points():
    z = np.random.default_rng(21706).standard_normal((500, 3))
    adjusted = numerical.moment_match(z)
    assert adjusted.mean(axis=0) == pytest.approx(np.zeros(3), abs=1e-12)
    assert adjusted.var(axis=0, ddof=1) == pytest.approx(np.ones(3), abs=1e-12)
    population = numerical.moment_match(z, ddof=0)
    assert population.var(axis=0, ddof=0) == pytest.approx(np.ones(3), abs=1e-12)


def test_moment_matching_constant_sample_cannot_define_scale():
    with pytest.raises(ValueError):
        numerical.moment_match([2, 2, 2])


def test_moment_matched_price_batches_against_analytic_bsm():
    rng = np.random.default_rng(21707)
    batch = []
    for _ in range(24):
        z = numerical.moment_match(rng.standard_normal(4096))
        terminal = 50 * np.exp((0.05 - 0.3**2 / 2) * 0.5 + 0.3 * math.sqrt(0.5) * z)
        batch.append(float(math.exp(-0.05 * 0.5) * np.maximum(terminal - 50, 0).mean()))
    summary = numerical.iid_summary(batch)
    # Finite-batch moment matching is not an exactly unbiased transformation.
    assert (
        abs(summary["estimate"] - bsm.call_price(50, 50, 0.05, 0.3, 0.5))
        < 6 * summary["standard_error"] + 0.002
    )


def test_unrandomized_1024_sobol_points_have_no_iid_standard_error():
    result = numerical.sobol_normal_points(10, dimension=2)
    cells = np.floor(result["uniforms"] * 8).astype(int)
    counts = np.zeros((8, 8), dtype=int)
    np.add.at(counts, (cells[:, 0], cells[:, 1]), 1)
    assert counts == pytest.approx(np.full((8, 8), 16), abs=1e-12)
    assert np.all(np.isfinite(result["normals"]))
    assert "standard_error" not in result
    assert result["uniforms"][0] == pytest.approx([0, 0], abs=1e-12)


def test_randomized_qmc_se_from_independent_scrambles():
    result = numerical.randomized_qmc_price(
        50, 50, 0.05, 0.3, 0.5, power=9, scrambles=24, seed=21708
    )
    assert result["standard_error"] == pytest.approx(
        np.std(result["samples"], ddof=1) / math.sqrt(24), abs=1e-12
    )
    assert result["payoff_evaluations"] == 24 * 512
    assert (
        abs(result["price"] - bsm.call_price(50, 50, 0.05, 0.3, 0.5)) < 6 * result["standard_error"]
    )


def test_conditional_uniform_endpoints_are_not_finite_quantiles():
    with pytest.raises(ValueError):
        numerical.conditional_call_from_uniforms(100, 150, 0.03, 0.2, 0.5, [0, 0.5])
