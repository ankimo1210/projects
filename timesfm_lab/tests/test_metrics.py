import numpy as np
import pytest
from timesfm_lab.baselines import QUANTILE_LEVELS

from timesfm_lab import metrics


def test_mase_of_seasonal_naive_on_pure_cycle_is_zero():
    x = np.tile([1.0, 5.0, 3.0, 9.0], 20)
    scale = metrics.seasonal_scale_mae(x, 4)
    # A perfectly periodic series has zero seasonal-difference error, so the
    # scale is degenerate and MASE is undefined rather than infinite.
    assert np.isnan(scale)
    assert np.isnan(metrics.mase(x[:4], x[:4], scale))


def test_mase_equals_one_when_error_matches_the_scale():
    rng = np.random.default_rng(0)
    ctx = np.cumsum(rng.normal(size=500))
    scale = metrics.seasonal_scale_mae(ctx, 1)
    actual = np.array([0.0, 0.0, 0.0])
    pred = actual + scale
    assert metrics.mase(actual, pred, scale) == pytest.approx(1.0)


def test_seasonal_scale_falls_back_to_lag_one_for_short_context():
    x = np.array([1.0, 2.0, 4.0])
    assert metrics.seasonal_scale_mae(x, 24) == pytest.approx(1.5)


def test_smape_is_zero_for_exact_forecast_including_zeros():
    a = np.array([0.0, 3.0, 0.0])
    assert metrics.smape(a, a) == pytest.approx(0.0)


def test_smape_saturates_at_200_for_opposite_signs():
    a = np.array([1.0, 1.0])
    p = np.array([-1.0, -1.0])
    assert metrics.smape(a, p) == pytest.approx(200.0)


def test_rmsse_matches_hand_computation():
    ctx = np.array([0.0, 1.0, 3.0, 6.0])  # lag-1 diffs 1,2,3 -> MSE 14/3
    actual = np.array([7.0])
    pred = np.array([9.0])
    expected = np.sqrt(4.0 / (14.0 / 3.0))
    assert metrics.rmsse(actual, pred, metrics.seasonal_scale_mse(ctx, 1)) == pytest.approx(expected)


def test_crps_of_a_point_mass_is_the_absolute_error():
    # Every quantile at the same value -> the quantile integral collapses to MAE.
    actual = np.array([5.0, 5.0])
    q = np.full((2, 9), 3.0)
    assert metrics.crps_from_quantiles(actual, q, QUANTILE_LEVELS) == pytest.approx(2.0, rel=1e-6)


def test_crps_rewards_a_well_placed_fan_over_a_point_mass():
    rng = np.random.default_rng(1)
    truth = rng.normal(size=400)
    from scipy.stats import norm

    good = np.tile(norm.ppf(QUANTILE_LEVELS), (400, 1))
    point = np.zeros((400, 9))
    assert metrics.crps_from_quantiles(truth, good, QUANTILE_LEVELS) < metrics.crps_from_quantiles(
        truth, point, QUANTILE_LEVELS
    )


def test_crps_rejects_a_mismatched_quantile_grid():
    with pytest.raises(ValueError):
        metrics.crps_from_quantiles(np.zeros(3), np.zeros((3, 5)), QUANTILE_LEVELS)
