"""Hull §23.5: likelihood conventions, printed leading rows and diagnostics."""

import math

import numpy as np
import pytest
from hullkit import _volatility_estimation as v
from scipy.optimize import minimize
from scipy.stats import chi2, norm

RAW_ACF = [
    0.537,
    0.556,
    0.352,
    0.351,
    0.334,
    0.413,
    0.326,
    0.353,
    0.295,
    0.259,
    0.233,
    0.168,
    0.169,
    0.168,
    0.200,
]
ADJUSTED_ACF = [
    0.022,
    -0.014,
    -0.001,
    0.046,
    -0.025,
    -0.005,
    -0.035,
    -0.023,
    0,
    0.064,
    -0.012,
    -0.024,
    -0.009,
    0.010,
    -0.005,
]


def test_source_bernoulli_and_zero_mean_gaussian_mle():
    assert v.bernoulli_mle(1, 10) == pytest.approx(0.1)

    def likelihood(p):
        return p * (1 - p) ** 9

    assert likelihood(0.1) > likelihood(0.09)
    assert likelihood(0.1) > likelihood(0.11)
    returns = [0.01, -0.02, 0.03]
    variance = v.estimate_variance(returns, center=False, ddof=0)
    result = v.conditional_likelihood(returns, [variance] * 3)
    # Hull omits additive constant and factor 1/2.
    density_reference = 2 * sum(
        norm.logpdf(u, scale=np.sqrt(variance)) for u in returns
    ) + 3 * math.log(2 * math.pi)
    assert result.sum() == pytest.approx(density_reference)


def test_source_table_23_1_first_four_likelihood_rows():
    prices = [2076.62, 2099.60, 2108.95, 2107.40, 2124.29, 2126.64]
    u = v.price_returns(prices)
    forecasts = v.garch_forecasts(u[1:], 0.0000039818, 0.223793, 0.747577, initial=u[0] ** 2)
    assert forecasts[:-1] == pytest.approx(
        [0.00012246, 0.00009997, 0.00007884, 0.00007729], abs=5e-9
    )
    loglik = v.conditional_likelihood(u[1:], forecasts[:-1])
    assert loglik == pytest.approx([8.845801, 9.205273, 8.633362, 9.452082], abs=1e-6)
    # Third published 8.6333 is not nearest rounding of 8.633362; preserve it.
    assert loglik[2] > 8.63335
    info = v.garch_characteristics(0.0000039818, 0.223793, 0.747577)
    assert info["long_variance"] == pytest.approx(0.0001391, abs=5e-8)


def test_source_table_23_2_all_30_acfs_and_chi_square_threshold():
    raw = v.ljung_box_from_acf(RAW_ACF, 1258)
    adjusted = v.ljung_box_from_acf(ADJUSTED_ACF, 1257)
    assert raw["statistic"] == pytest.approx(2139.61, abs=0.005)
    assert adjusted["statistic"] == pytest.approx(12.94915, abs=0.00001)
    assert raw["statistic"] != pytest.approx(2170, abs=1)
    assert adjusted["statistic"] != pytest.approx(13.2, abs=0.1)
    assert chi2.ppf(0.95, 15) == pytest.approx(25, abs=0.005)
    assert raw["p_value"] < 0.05 < adjusted["p_value"]


def test_acf_pairwise_pearson_and_global_centering_are_explicit():
    data = np.array([1, 2, 4, 8, 3, 2, 6, 1], dtype=float)
    hull = v.autocorrelations(data, 3)
    global_acf = v.autocorrelations(data, 3, convention="global")
    centered = data - data.mean()
    for lag in range(1, 4):
        assert hull[lag - 1] == pytest.approx(np.corrcoef(data[:-lag], data[lag:])[0, 1])
        assert global_acf[lag - 1] == pytest.approx(
            sum(centered[i] * centered[i + lag] for i in range(len(data) - lag)) / sum(centered**2)
        )
    assert v.ljung_box_from_acf(hull, 8, estimated_parameters=1)["degrees"] == 2


def test_ewma_fit_against_independent_grid_likelihood():
    u = np.random.default_rng(235).normal(size=160) * np.linspace(0.005, 0.03, 160)
    initial = 0.0001
    fit = v.fit_ewma(u, initial=initial)

    def objective(decay):
        variance = initial
        score = 0
        for move in u:
            score += math.log(variance) + move * move / variance
            variance = decay * variance + (1 - decay) * move * move
        return score

    grid = np.linspace(0.001, 0.999, 400)
    assert objective(fit["decay"]) <= min(objective(x) for x in grid) + 1e-7
    assert fit["measure"] == pytest.approx(-objective(fit["decay"]))


def test_variance_targeting_fit_against_separate_optimizer_and_recursion():
    u = np.random.default_rng(236).normal(size=220) * np.r_[np.full(110, 0.01), np.full(110, 0.02)]
    target = float(np.mean(u * u))
    fit = v.fit_garch(u, initial=target, target_variance=target)

    def objective(parameters):
        alpha, beta = parameters
        if min(alpha, beta) < 0 or alpha + beta >= 1:
            return 1e20
        omega = (1 - alpha - beta) * target
        variance, score = target, 0
        for move in u:
            score += math.log(variance) + move * move / variance
            variance = omega + alpha * move * move + beta * variance
        return score

    other = minimize(
        objective,
        [0.12, 0.85],
        method="Nelder-Mead",
        options={"xatol": 1e-9, "fatol": 1e-8, "maxiter": 2000},
    )
    assert other.success
    assert fit["measure"] == pytest.approx(-other.fun, abs=2e-5)
    assert fit["omega"] == pytest.approx((1 - fit["alpha"] - fit["beta"]) * target)


def test_three_parameter_fit_reports_convergence_and_explicit_hull_start():
    u = np.random.default_rng(237).normal(size=140) * np.linspace(0.01, 0.025, 140)
    fit = v.fit_garch(u, initial=u[0] ** 2, hull_start=True)
    assert fit["success"]
    assert fit["omega"] > 0
    assert 0 <= fit["alpha"] + fit["beta"] < 1
    forecasts = v.garch_forecasts(u[1:], fit["omega"], fit["alpha"], fit["beta"], initial=u[0] ** 2)
    assert fit["measure"] == pytest.approx(v.conditional_likelihood(u[1:], forecasts[:-1]).sum())
    with pytest.raises(ValueError):
        v.conditional_likelihood([0.01], [0])
