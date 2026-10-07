"""Hull22.1 risk definitions and limits of square-root time scaling."""

import math

import numpy as np
import pytest
from hullkit import _market_risk as market
from scipy.integrate import quad
from scipy.stats import norm, t


def test_normal_loss_sign_mean_and_independent_tail_integral():
    result = market.normal_loss_risk(2, 0.99, loss_mean=0.3, horizon=4)
    z = norm.ppf(0.99)
    assert result["var"] == pytest.approx(1.2 + 4 * z, abs=1e-12)
    expected = quad(lambda x: x * norm.pdf(x, loc=1.2, scale=4), result["var"], np.inf)[0] / 0.01
    assert result["es"] == pytest.approx(expected, abs=1e-9)
    assert result["sigma"] == pytest.approx(4, abs=1e-12)


def test_same_var_normal_and_student_t_have_different_tail_expectations():
    normal = market.normal_loss_risk(3 / norm.ppf(0.99))
    heavy = market.student_loss_risk(3 / t.ppf(0.99, 5), 5)
    assert normal["var"] == pytest.approx(3, abs=1e-12)
    assert heavy["var"] == pytest.approx(3, abs=1e-12)
    assert heavy["es"] > normal["es"]
    scale = 3 / t.ppf(0.99, 5)
    integrated = quad(lambda x: x * t.pdf(x, 5, scale=scale), 3, np.inf)[0] / 0.01
    assert heavy["es"] == pytest.approx(integrated, abs=1e-8)


@pytest.mark.parametrize("phi,printed_ratio", [(0, 1), (0.1, 1.094), (0.3, 1.317), (-0.3, None)])
def test_ar1_horizon_covariance_sum_and_iid_limit(phi, printed_ratio):
    result = market.ar1_horizon_risk(2, phi, 10)
    covariance = 4 * phi ** np.abs(np.arange(10)[:, None] - np.arange(10))
    assert result["sigma"] ** 2 == pytest.approx(np.ones(10) @ covariance @ np.ones(10), abs=1e-11)
    if printed_ratio is not None:
        assert result["sqrt_time_ratio"] == pytest.approx(printed_ratio, abs=0.0006)
    if phi == 0:
        assert result["var"] == pytest.approx(
            market.normal_loss_risk(2, horizon=10)["var"], abs=1e-12
        )


def test_fixed_seed_ar1_aggregate_quantile_matches_closed_form_with_quantile_se():
    rng = np.random.default_rng(2201)
    count, days, phi = 100_000, 10, 0.3
    daily = rng.normal(size=count)
    sums = daily.copy()
    for _ in range(days - 1):
        daily = phi * daily + math.sqrt(1 - phi**2) * rng.normal(size=count)
        sums += daily
    reference = market.ar1_horizon_risk(1, phi, days)
    density = norm.pdf(norm.ppf(0.99)) / reference["sigma"]
    se = math.sqrt(0.99 * 0.01 / count) / density
    assert np.quantile(sums, 0.99) == pytest.approx(reference["var"], abs=6 * se)
    assert reference["sqrt_time_ratio"] > 1.3


def test_invalid_probability_or_nonstationary_ar1_is_rejected():
    with pytest.raises(ValueError):
        market.normal_loss_risk(-1)
    with pytest.raises(ValueError):
        market.normal_loss_risk(1, 1)
    with pytest.raises(ValueError):
        market.ar1_horizon_risk(1, 1, 10)
    with pytest.raises(ValueError):
        market.student_loss_risk(1, 1)
