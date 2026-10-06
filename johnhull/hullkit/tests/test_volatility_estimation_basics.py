"""Hull §23.1 estimators: source formulas, independent small-sample arithmetic."""

import math

import numpy as np
import pytest
from hullkit import _volatility_estimation as v


def test_log_sample_vs_simple_zero_mean_variance_source_conventions():
    prices = [100, 101, 103.02, 101.9898]
    simple = v.price_returns(prices)
    logarithmic = v.price_returns(prices, kind="log")
    assert simple == pytest.approx([0.01, 0.02, -0.01])
    reference = [math.log(prices[i + 1]) - math.log(prices[i]) for i in range(3)]
    assert logarithmic == pytest.approx(reference)
    assert v.estimate_variance(logarithmic) == pytest.approx(
        sum((x - sum(reference) / 3) ** 2 for x in reference) / 2
    )
    assert v.estimate_variance(simple, center=False, ddof=0) == pytest.approx(0.0002)


def test_zero_mean_mle_independent_normal_log_likelihood_minimum():
    returns = np.array([0.01, -0.02, 0.03, -0.01])
    estimate = v.estimate_variance(returns, center=False, ddof=0)

    def objective(variance):
        return sum(math.log(variance) + x * x / variance for x in returns)

    assert objective(estimate) < objective(estimate * 0.8)
    assert objective(estimate) < objective(estimate * 1.2)


def test_arch_weights_and_long_run_intercept():
    history = [0.01, -0.02, 0.03]
    result = v.arch_forecast(history, [0.1, 0.2, 0.4], long_variance=0.0004, long_weight=0.3)
    assert result == pytest.approx(0.1 * 0.01**2 + 0.2 * 0.02**2 + 0.4 * 0.03**2 + 0.3 * 0.0004)
    assert v.arch_forecast([0.02] * 3, [0.2, 0.3, 0.5]) == pytest.approx(0.0004)
    with pytest.raises(ValueError):
        v.arch_forecast(history, [0.2, 0.3, 0.6])


def test_estimator_degenerate_and_undefined_denominator():
    assert v.estimate_variance([0.01] * 4) == pytest.approx(0)
    assert v.estimate_variance([0.01] * 4, center=False, ddof=0) == pytest.approx(0.0001)
    with pytest.raises(ValueError):
        v.estimate_variance([0.01], ddof=1)
