from __future__ import annotations

import numpy as np
import pytest
from quant_textbook.advanced_learning import (
    feature_drift_report,
    fit_decision_stump,
    fit_gaussian_process,
    fit_gradient_boosting,
    fit_kernel_ridge,
    fit_kmeans,
    split_conformal_interval,
)


def test_decision_stump_finds_the_only_material_split() -> None:
    features = np.linspace(-2.0, 2.0, 200)[:, None]
    target = np.where(features[:, 0] <= 0.0, -1.0, 2.0)
    stump = fit_decision_stump(
        features,
        target,
        min_leaf_size=20,
        max_thresholds_per_feature=256,
    )
    assert abs(stump.threshold) < 0.03
    np.testing.assert_allclose(stump.predict(features), target)
    assert stump.squared_error < 1e-12


def test_gradient_boosting_loss_is_monotone_and_beats_the_mean() -> None:
    rng = np.random.default_rng(2001)
    features = rng.uniform(-2.0, 2.0, size=(500, 2))
    target = np.sin(features[:, 0]) + 0.4 * features[:, 1] ** 2 + rng.normal(scale=0.05, size=500)
    model = fit_gradient_boosting(
        features, target, n_estimators=60, learning_rate=0.08, min_leaf_size=15
    )
    assert np.all(np.diff(model.training_loss) <= 1e-12)
    assert np.mean((target - model.predict(features)) ** 2) < 0.35 * np.var(target)


def test_kernel_ridge_is_column_scale_invariant_and_fits_smooth_signal() -> None:
    features = np.linspace(-3.0, 3.0, 160)[:, None]
    target = np.sin(features[:, 0])
    model = fit_kernel_ridge(features, target, length_scale=0.8, ridge=1e-3)
    scaled = fit_kernel_ridge(features * 1e12, target, length_scale=0.8, ridge=1e-3)
    np.testing.assert_allclose(model.predict(features), scaled.predict(features * 1e12), atol=1e-10)
    assert np.sqrt(np.mean((target - model.predict(features)) ** 2)) < 0.01


def test_gaussian_process_returns_finite_uncertainty_and_respects_scaling() -> None:
    features = np.linspace(-2.0, 2.0, 80)[:, None]
    target = np.cos(features[:, 0])
    model = fit_gaussian_process(features, target, length_scale=0.7, noise_variance=1e-4)
    prediction = model.predict(features)
    assert np.all(np.isfinite(prediction.mean))
    assert np.all(prediction.standard_deviation > 0.0)
    assert np.sqrt(np.mean((target - prediction.mean) ** 2)) < 0.01


def test_gp_mean_matches_kernel_ridge_under_equivalent_regularization() -> None:
    features = np.linspace(-2.0, 2.0, 60)[:, None]
    target = np.sin(features[:, 0]) + 0.2 * features[:, 0]
    noise_variance = 0.03
    signal_variance = float(np.var(target - target.mean()))
    gp = fit_gaussian_process(
        features,
        target,
        length_scale=0.9,
        noise_variance=noise_variance,
    )
    kernel_ridge = fit_kernel_ridge(
        features,
        target,
        length_scale=0.9,
        ridge=noise_variance / signal_variance,
    )
    np.testing.assert_allclose(
        gp.predict(features).mean,
        kernel_ridge.predict(features),
        atol=1e-10,
    )


def test_kmeans_uses_explicit_rng_and_separates_two_clouds() -> None:
    rng = np.random.default_rng(2002)
    features = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.2, size=(100, 2)),
            rng.normal(loc=2.0, scale=0.2, size=(100, 2)),
        ]
    )
    model = fit_kmeans(features, 2, rng=np.random.default_rng(99))
    assert model.converged
    assert np.unique(model.labels[:100]).size == 1
    assert np.unique(model.labels[100:]).size == 1
    assert model.labels[0] != model.labels[-1]


def test_feature_drift_distinguishes_identical_and_shifted_periods() -> None:
    rng = np.random.default_rng(2003)
    reference = rng.normal(size=(1000, 3))
    identical = feature_drift_report(reference, reference.copy())
    assert identical.maximum_absolute_mean_difference == pytest.approx(0.0)
    assert identical.maximum_population_stability_index == pytest.approx(0.0)

    current = reference.copy()
    current[:, 1] += 1.5
    shifted = feature_drift_report(reference, current, feature_names=("a", "b", "c"))
    assert shifted.maximum_absolute_mean_difference > 1.0
    assert shifted.population_stability_index[1] > 0.5


def test_split_conformal_uses_finite_sample_higher_quantile() -> None:
    actual = np.arange(9.0)
    calibration_prediction = actual + np.arange(1.0, 10.0)
    interval = split_conformal_interval(
        actual,
        calibration_prediction,
        np.array([10.0, 20.0]),
        miscoverage=0.2,
    )
    # ceil((9 + 1) * 0.8) = rank 8.
    assert interval.residual_quantile == pytest.approx(8.0)
    np.testing.assert_allclose(interval.lower, [2.0, 12.0])
    np.testing.assert_allclose(interval.upper, [18.0, 28.0])


@pytest.mark.parametrize(
    "call",
    [
        lambda: fit_decision_stump([[1.0], [1.0]], [0.0, 1.0], min_leaf_size=1),
        lambda: fit_gradient_boosting([[1.0], [2.0]], [0.0], n_estimators=2),
        lambda: fit_kernel_ridge([[1.0], [2.0]], [0.0, 1.0], ridge=0.0),
        lambda: fit_gaussian_process([[1.0], [2.0]], [0.0, 1.0], noise_variance=0.0),
        lambda: fit_kmeans([[1.0], [2.0]], 2, rng=np.random.default_rng(1)),
        lambda: feature_drift_report([[1.0]], [[1.0, 2.0]]),
        lambda: split_conformal_interval([1.0], [1.0], [1.0]),
    ],
)
def test_advanced_learning_helpers_reject_invalid_contracts(call) -> None:
    with pytest.raises((TypeError, ValueError)):
        call()
