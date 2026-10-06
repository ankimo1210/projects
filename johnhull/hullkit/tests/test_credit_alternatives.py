"""Hull §25.11 computational alternatives; all extra parameters explicitly synthetic."""

import math
from itertools import pairwise, product

import numpy as np
import pytest
from hullkit import _credit_alternatives as a
from hullkit import _credit_portfolio_extensions as e
from scipy.integrate import quad
from scipy.special import expit
from scipy.stats import norm, t


def test_heterogeneous_loadings_asb_against_all_default_states_adaptive_integral():
    pd = np.array([0.02, 0.07, 0.12, 0.2])
    load = np.array([0.1, 0.45, -0.3, 0.6])
    thresholds = norm.ppf(pd)
    reference = np.zeros(5)
    for state in product((0, 1), repeat=4):

        def density(f, state=state):
            p = norm.cdf((thresholds - load * f) / np.sqrt(1 - load * load))
            return math.prod(p[i] if state[i] else 1 - p[i] for i in range(4)) * norm.pdf(f)

        reference[sum(state)] += quad(density, -12, 12, epsabs=1e-12)[0]
    result = a.heterogeneous_factor_counts(pd, load, nodes=160)
    assert result["pmf"] == pytest.approx(reference, abs=1e-11)
    assert sum(result["pmf"]) == pytest.approx(1)
    assert np.arange(5) @ result["pmf"] == pytest.approx(sum(pd))


def test_heterogeneous_homogeneous_limit_and_individual_zero_one_pds():
    result = a.heterogeneous_factor_counts([0.04] * 12, [math.sqrt(0.2)] * 12)
    assert result["pmf"] == pytest.approx(e.default_count_distribution(12, 0.04, 0.2))
    boundary = a.heterogeneous_factor_counts([0, 1], [0.3, -0.4])
    assert boundary["pmf"] == pytest.approx([0, 1, 0])


def test_source_nu_four_double_t_against_independent_convolution_and_t_mc():
    result = a.double_t_counts(12, 0.04, 0.15, nu=4, nodes=240, threshold_nodes=320)
    scale = math.sqrt(0.5)
    threshold = result["threshold"]
    # Independent adaptive convolution of two independent standardized t variates.
    cdf = quad(
        lambda f: (
            t.pdf(f / scale, 4)
            / scale
            * t.cdf((threshold - math.sqrt(0.15) * f) / (math.sqrt(0.85) * scale), 4)
        ),
        -np.inf,
        np.inf,
        epsabs=1e-10,
    )[0]
    assert cdf == pytest.approx(0.04, abs=3e-6)
    rng = np.random.default_rng(2511)
    latent = math.sqrt(0.15) * scale * rng.standard_t(4, size=(220_000, 1)) + math.sqrt(
        0.85
    ) * scale * rng.standard_t(4, size=(220_000, 12))
    counts = (latent <= threshold).sum(axis=1)
    for k in (1, 2, 6):
        observed = (counts >= k).astype(float)
        assert abs(observed.mean() - result["pmf"][k:].sum()) <= 6 * observed.std(
            ddof=1
        ) / math.sqrt(counts.size)
    observed = counts / 12
    assert abs(observed.mean() - 0.04) <= 6 * observed.std(ddof=1) / math.sqrt(counts.size)


def test_factor_dependent_recovery_loading_recalibrates_pd_and_matches_terminal_loss_mc():
    def loading(f):
        return 0.4 + 0.2 * expit(-np.asarray(f))

    def recovery(f):
        return 0.4 + 0.12 * np.tanh(f)

    result = a.factor_dependent_pool(40, 0.08, loading, recovery, 0.03, 0.15, nodes=160)
    assert result["marginal_pd"] == pytest.approx(0.08, abs=1e-10)
    rng = np.random.default_rng(25114)
    factor = rng.normal(size=220_000)
    load = loading(factor)
    latent = load[:, None] * factor[:, None] + np.sqrt(1 - load[:, None] ** 2) * rng.normal(
        size=(factor.size, 40)
    )
    count = (latent <= result["threshold"]).sum(axis=1)
    sample = np.clip((count * (1 - recovery(factor)) / 40 - 0.03) / 0.12, 0, 1)
    assert abs(sample.mean() - result["expected_tranche_loss"]) <= 6 * sample.std(
        ddof=1
    ) / math.sqrt(factor.size)
    observed = count / 40
    assert abs(observed.mean() - 0.08) <= 6 * observed.std(ddof=1) / math.sqrt(factor.size)
    average = (observed * recovery(factor)).mean() / observed.mean()
    influence = observed * (recovery(factor) - average) / observed.mean()
    assert abs(average - result["recovery_given_default"]) <= 6 * influence.std(ddof=1) / math.sqrt(
        factor.size
    )
    assert result["recovery_given_default"] < 0.4
    constant = a.factor_dependent_pool(10, 0.08, lambda f: 0.5, lambda f: 0.4, 0, 1)
    assert constant["threshold"] == pytest.approx(norm.ppf(0.08), abs=1e-10)
    assert constant["expected_tranche_loss"] == pytest.approx(0.08 * 0.6)


HAZARDS = np.array([0.005, 0.04, 0.25])
WEIGHTS = np.array([0.2, 0.5, 0.3])
BOUNDS = np.array([0, 0.15, 0.45, 1])


def test_hazard_mixture_legs_against_all_default_year_cashflow_states():
    result = a.hazard_mixture_legs(HAZARDS, WEIGHTS, 0.4, 0.03, 2, BOUNDS, 4, frequency=1)
    reference = np.zeros((3, 3))
    for hazard, mixture_weight in zip(HAZARDS, WEIGHTS, strict=True):
        probabilities = [
            1 - math.exp(-hazard),
            math.exp(-hazard) - math.exp(-2 * hazard),
            math.exp(-2 * hazard),
        ]
        for states in product(range(3), repeat=4):
            probability = mixture_weight * math.prod(probabilities[s] for s in states)
            for index, (lo, hi) in enumerate(pairwise(BOUNDS)):
                remaining = 1.0
                for year in (1, 2):
                    count = sum(s < year for s in states)
                    lost = max(0, min(hi - lo, 0.15 * count - lo)) / (hi - lo)
                    new = 1 - lost
                    reference[index, 0] += probability * new * math.exp(-0.03 * year)
                    reference[index, 1] += (
                        probability * 0.5 * (remaining - new) * math.exp(-0.03 * (year - 0.5))
                    )
                    reference[index, 2] += (
                        probability * (remaining - new) * math.exp(-0.03 * (year - 0.5))
                    )
                    remaining = new
    assert np.column_stack(
        [result[k] for k in ("annuity", "accrual", "protection")]
    ) == pytest.approx(reference, abs=2e-14)


def _synthetic_quotes():
    legs = a.hazard_mixture_legs(HAZARDS, WEIGHTS, 0.4, 0.03, 2, BOUNDS, 4, frequency=1)
    quotes = legs["spread"].copy()
    quotes[0] = legs["protection"][0] - 0.05 * (legs["annuity"][0] + legs["accrual"][0])
    return quotes


def test_implied_hazard_mixture_nonnegative_weights_recovers_known_synthetic_distribution():
    quotes = _synthetic_quotes()
    result = a.calibrate_hazard_mixture(
        HAZARDS,
        quotes,
        0.4,
        0.03,
        2,
        BOUNDS,
        4,
        frequency=1,
        quote_kinds=["upfront", "spread", "spread"],
        fixed_coupons=[0.05, 0, 0],
    )
    assert result["weights"] == pytest.approx(WEIGHTS, abs=2e-10)
    assert result["model_quotes"] == pytest.approx(quotes, abs=1e-11)
    assert result["linear_rank"] == 3
    assert result["unique_linear_solution"]


def test_duplicate_hazard_nodes_have_nonunique_weights_but_reprice_same_quotes():
    quotes = _synthetic_quotes()
    result = a.calibrate_hazard_mixture(
        [0.005, 0.04, 0.04, 0.25],
        quotes,
        0.4,
        0.03,
        2,
        BOUNDS,
        4,
        frequency=1,
        quote_kinds=["upfront", "spread", "spread"],
        fixed_coupons=[0.05, 0, 0],
    )
    assert not result["unique_linear_solution"]
    assert result["weights"].sum() == pytest.approx(1)
    assert np.all(result["weights"] >= 0)
    assert result["model_quotes"] == pytest.approx(quotes, abs=1e-11)
    for weights in ([0.2, 0.2, 0.3, 0.3], [0.2, 0.4, 0.1, 0.3]):
        legs = a.hazard_mixture_legs(
            [0.005, 0.04, 0.04, 0.25], weights, 0.4, 0.03, 2, BOUNDS, 4, frequency=1
        )
        assert legs["spread"][1:] == pytest.approx(quotes[1:])


def test_invalid_probability_loading_nu_weights_and_infeasible_quotes():
    with pytest.raises(ValueError):
        a.heterogeneous_factor_counts([1.1], [0.3])
    with pytest.raises(ValueError):
        a.double_t_counts(10, 0.04, 0.2, nu=2)
    with pytest.raises(ValueError):
        a.factor_dependent_pool(10, 0.1, lambda f: 1.1, lambda f: 0.4, 0, 1)
    with pytest.raises(ValueError):
        a.hazard_mixture_legs(HAZARDS, [0.2, 0.5, 0.4], 0.4, 0.03, 2, BOUNDS, 4)
    with pytest.raises(ValueError):
        a.calibrate_hazard_mixture(HAZARDS, [100, 100, 100], 0.4, 0.03, 2, BOUNDS, 4)


@pytest.mark.parametrize("loading", [0.999, -0.999, 0.995, -0.995])
@pytest.mark.parametrize("pd", [0.02, 0.001])
def test_review_r5_near_perfect_factor_preserves_pd_mean_count_and_pool_loss(loading, pd):
    count = a.heterogeneous_factor_counts([pd] * 10, loading)
    assert np.arange(11) @ count["pmf"] == pytest.approx(10 * pd, abs=2e-10)
    assert count["pmf"].sum() == pytest.approx(1, abs=2e-11)
    pool = a.factor_dependent_pool(10, pd, lambda f: loading, lambda f: 0.4, 0, 1)
    assert pool["marginal_pd"] == pytest.approx(pd, abs=2e-11)
    assert pool["expected_tranche_loss"] == pytest.approx(0.6 * pd, abs=2e-11)
    assert pool["threshold"] == pytest.approx(norm.ppf(pd), abs=2e-8)


def test_review_r5_double_t_rare_pd_high_loading_preserves_actual_marginal():
    result = a.double_t_counts(10, 0.0001, 0.99)
    scale = math.sqrt(0.5)
    threshold = result["threshold"]
    actual = quad(
        lambda f: (
            t.pdf(f / scale, 4)
            / scale
            * t.cdf((threshold - math.sqrt(0.99) * f) / (math.sqrt(0.01) * scale), 4)
        ),
        -np.inf,
        np.inf,
        epsabs=1e-11,
        epsrel=1e-11,
    )[0]
    assert actual == pytest.approx(0.0001, abs=2e-10)
    assert result["marginal_pd"] == pytest.approx(actual, abs=2e-10)
    assert np.arange(11) @ result["pmf"] == pytest.approx(0.001, abs=2e-9)
