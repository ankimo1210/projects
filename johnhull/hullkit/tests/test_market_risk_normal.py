"""Hull22.3 domestic money risk, source rounding and lognormal comparison."""

import math

import numpy as np
import pytest
from hullkit import _market_risk as market
from scipy.integrate import quad
from scipy.stats import lognorm, norm


@pytest.mark.parametrize(
    "amounts,vols,corr,var_print,es_exact",
    [
        ([10_000_000], [0.02], [[1]], 1_471_300, 1_685_629.5),
        ([5_000_000], [0.01], [[1]], 367_800, 421_407.4),
        ([10_000_000, 5_000_000], [0.02, 0.01], [[1, 0.3], [0.3, 1]], 1_620_100, 1_856_106.9),
    ],
)
def test_source_microsoft_att_and_portfolio_prices(amounts, vols, corr, var_print, es_exact):
    result = market.normal_portfolio_risk(amounts, vols, corr, horizon=10)
    assert result["var"] == pytest.approx(var_print, abs=50)
    assert result["es"] == pytest.approx(es_exact, abs=0.1)


def test_microsoft_printed_es_uses_rounded_density_quantile():
    exact = market.normal_loss_risk(200_000, horizon=10)["es"]
    rounded = market.source_normal_es(200_000, 2.326, horizon=10)
    assert rounded == pytest.approx(1_687_000, abs=10)
    assert abs(exact - 1_687_000) > 1000
    integrated = (
        quad(lambda z: z * norm.pdf(z), norm.ppf(0.99), np.inf)[0] * 200_000 * math.sqrt(10) / 0.01
    )
    assert exact == pytest.approx(integrated, abs=1e-6)


def test_daily_annual_volatility_units_and_nonzero_profit_mean():
    units = market.volatility_units(0.02)
    assert units["annual"] == pytest.approx(0.3174901573, abs=1e-10)
    assert units["daily_to_annual_ratio"] == pytest.approx(1 / math.sqrt(252), abs=1e-12)
    result = market.normal_portfolio_risk(
        [10_000_000], [0.02], [[1]], horizon=10, daily_mean_returns=[0.2 / 252]
    )
    assert result["mean"] == pytest.approx(-10_000_000 * 0.2 / 252 * 10, abs=1e-8)
    assert result["var"] == pytest.approx(1_471_311.58237 - 10_000_000 * 0.2 / 252 * 10, abs=0.001)


@pytest.mark.parametrize("days", [1, 10])
def test_lognormal_loss_var_and_es_by_independent_density_integral(days):
    result = market.lognormal_position_risk(10_000_000, 0.02, days, growth=0.2 / 252)
    shape = 0.02 * math.sqrt(days)
    scale = 10_000_000 * math.exp((0.2 / 252 - 0.02**2 / 2) * days)
    cutoff = lognorm.ppf(0.01, s=shape, scale=scale)
    assert result["var"] == pytest.approx(10_000_000 - cutoff, abs=1e-7)
    # Integrate the standard normal latent variable, using a separately defined payoff.
    expected = (
        quad(
            lambda z: (10_000_000 - scale * math.exp(shape * z)) * norm.pdf(z), -11, norm.ppf(0.01)
        )[0]
        / 0.01
    )
    assert result["es"] == pytest.approx(expected, abs=1e-6)


def test_lognormal_one_day_approximation_does_not_justify_long_horizon_sqrt_scaling():
    one = market.lognormal_position_risk(10_000_000, 0.02, 1)
    normal = market.normal_loss_risk(200_000)
    assert abs(one["var"] / normal["var"] - 1) < 0.025
    long = market.lognormal_position_risk(10_000_000, 0.02, 100)
    assert abs(long["var"] / (one["var"] * 10) - 1) > 0.1


def test_fixed_seed_correlated_linear_portfolio_var_and_es_with_sampling_se():
    rng = np.random.default_rng(2203)
    count = 150_000
    correlation = np.array([[1, 0.3], [0.3, 1]])
    shocks = rng.multivariate_normal([0, 0], correlation, count)
    losses = -(shocks * np.array([0.02, 0.01])) @ np.array([10_000_000, 5_000_000])
    result = market.normal_portfolio_risk([10_000_000, 5_000_000], [0.02, 0.01], correlation)
    sampled = market.empirical_risk(-losses)
    density = norm.pdf(norm.ppf(0.99)) / result["sigma"]
    var_se = math.sqrt(0.99 * 0.01 / count) / density
    es_se = np.maximum(losses - result["var"], 0).std(ddof=1) / math.sqrt(count) / 0.01
    assert sampled["var"] == pytest.approx(result["var"], abs=6 * var_se)
    assert sampled["es"] == pytest.approx(result["es"], abs=6 * es_se)


def test_fractional_empirical_tail_remains_defined_near_one_confidence():
    result = market.empirical_risk([-1, -2, -3], np.nextafter(1.0, 0.0), es_rule="tail_mass")
    assert result["es"] == pytest.approx(3, abs=1e-12)
