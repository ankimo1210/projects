from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from quant_textbook.learning import (
    calibration_table,
    chronological_split,
    classification_metrics,
    expanding_window_splits,
    fit_elastic_net,
    fit_gaussian_classifier,
    fit_lasso,
    fit_logistic_ridge,
    fit_ridge,
    knn_predict_proba,
    make_treasury_forecast_dataset,
    predict_gaussian_proba,
    regression_metrics,
)
from quant_textbook.treasury_data import TREASURY_METHOD_BREAK, load_treasury_snapshot


def test_real_treasury_forecast_dataset_has_strictly_future_targets_and_no_missing_values() -> None:
    treasury = load_treasury_snapshot()
    dataset = make_treasury_forecast_dataset(treasury.frame)
    # Twenty realized changes are needed for the first volatility feature, the
    # final row has no next-publication target, and one target crossing the
    # official 2021-12-06 methodology break is intentionally removed.
    assert dataset.features.shape[0] == treasury.metadata.row_count - 22
    assert dataset.features.shape[1] == len(dataset.feature_names)
    assert np.all(dataset.target_dates > dataset.prediction_dates)
    assert np.all(np.isfinite(dataset.features))
    assert np.all(np.isfinite(dataset.regression_target))
    assert set(np.unique(dataset.direction_target)) == {0, 1}
    assert np.any(dataset.prediction_dates < TREASURY_METHOD_BREAK.to_datetime64())
    assert np.any(dataset.prediction_dates >= TREASURY_METHOD_BREAK.to_datetime64())
    crosses_break = (dataset.prediction_dates < TREASURY_METHOD_BREAK.to_datetime64()) & (
        dataset.target_dates >= TREASURY_METHOD_BREAK.to_datetime64()
    )
    assert not np.any(crosses_break)
    assert "18:00" in dataset.availability_contract

    with pytest.raises(ValueError, match="later than"):
        replace(dataset, target_dates=dataset.prediction_dates.copy())


def test_chronological_and_expanding_splits_purge_boundaries_without_overlap() -> None:
    split = chronological_split(100, gap=2)
    assert split.train.max() < split.validation.min() - 1
    assert split.validation.max() < split.test.min() - 1
    assert not set(split.train) & set(split.validation)
    assert not set(split.validation) & set(split.test)

    folds = expanding_window_splits(80, initial_train_size=40, test_size=10, step=10, gap=2)
    assert len(folds) == 3
    for train, test in folds:
        assert train.max() + 2 < test.min()
        assert np.array_equal(train, np.arange(train.size))


def test_ridge_recovers_prediction_under_extreme_column_rescaling() -> None:
    rng = np.random.default_rng(1001)
    features = rng.normal(size=(300, 3))
    target = 1.5 + features @ np.array([2.0, -0.7, 0.4]) + rng.normal(scale=0.05, size=300)
    reference = fit_ridge(features, target, alpha=1e-6)
    scaled = features * np.array([1e-12, 1e7, 1e3])
    scaled_model = fit_ridge(scaled, target, alpha=1e-6)
    np.testing.assert_allclose(
        reference.predict(features), scaled_model.predict(scaled), atol=1e-10
    )


def test_unpenalized_ridge_path_handles_exactly_redundant_columns() -> None:
    feature = np.linspace(-2.0, 2.0, 100)
    features = np.column_stack([feature, 2.0 * feature])
    target = 1.5 + 3.0 * feature
    model = fit_ridge(features, target, alpha=0.0)
    assert model.converged
    np.testing.assert_allclose(model.predict(features), target, atol=1e-12)


def test_lasso_and_elastic_net_produce_sparse_converged_solutions() -> None:
    rng = np.random.default_rng(1002)
    features = rng.normal(size=(500, 8))
    target = 2.0 * features[:, 0] - 1.5 * features[:, 3] + rng.normal(scale=0.1, size=500)
    lasso = fit_lasso(features, target, alpha=0.15)
    elastic = fit_elastic_net(features, target, alpha=0.1, l1_ratio=0.7)
    assert lasso.converged and elastic.converged
    assert np.sum(np.abs(lasso.coefficients) < 1e-12) >= 5
    assert regression_metrics(target, lasso.predict(features)).rmse < 0.4
    standardized = (features - lasso.feature_mean) / lasso.feature_scale
    residual = target - lasso.predict(features)
    correlations = standardized.T @ residual / features.shape[0]
    active = np.abs(lasso.coefficients) > 1e-10
    np.testing.assert_allclose(
        correlations[active],
        lasso.alpha * np.sign(lasso.coefficients[active]),
        atol=1e-8,
    )
    assert np.all(np.abs(correlations[~active]) <= lasso.alpha + 1e-8)


def test_logistic_ridge_is_scale_invariant_and_improves_on_constant_probability() -> None:
    rng = np.random.default_rng(1003)
    features = rng.normal(size=(800, 2))
    probabilities = 1.0 / (1.0 + np.exp(-(0.3 + features @ np.array([1.2, -0.8]))))
    target = rng.binomial(1, probabilities)
    model = fit_logistic_ridge(features, target, alpha=1e-3)
    scaled = fit_logistic_ridge(features * np.array([1e-10, 1e10]), target, alpha=1e-3)
    assert model.converged and scaled.converged
    np.testing.assert_allclose(
        model.predict_proba(features),
        scaled.predict_proba(features * np.array([1e-10, 1e10])),
        atol=1e-10,
    )
    fitted_metrics = classification_metrics(target, model.predict_proba(features))
    constant_metrics = classification_metrics(target, np.full(target.size, target.mean()))
    assert fitted_metrics.log_loss < constant_metrics.log_loss


@pytest.mark.parametrize("kind", ["lda", "qda", "naive_bayes"])
def test_gaussian_classifiers_and_knn_separate_a_simple_problem(kind: str) -> None:
    rng = np.random.default_rng(1004)
    negative = rng.normal(loc=-1.0, scale=0.6, size=(150, 2))
    positive = rng.normal(loc=1.0, scale=0.6, size=(150, 2))
    features = np.vstack([negative, positive])
    target = np.r_[np.zeros(150), np.ones(150)]
    model = fit_gaussian_classifier(features, target, kind=kind)
    probability = predict_gaussian_proba(model, features)
    scaled_features = features * np.array([1e-10, 1e10])
    scaled_model = fit_gaussian_classifier(scaled_features, target, kind=kind)
    scaled_probability = predict_gaussian_proba(scaled_model, scaled_features)
    assert classification_metrics(target, probability).accuracy > 0.95
    np.testing.assert_allclose(probability, scaled_probability, atol=1e-10)
    knn_probability = knn_predict_proba(features, target, features[:20], n_neighbors=11)
    assert np.all(knn_probability < 0.2)


def test_metrics_and_calibration_table_match_known_values() -> None:
    actual = np.array([0.0, 1.0, 1.0, 0.0])
    probability = np.array([0.1, 0.8, 0.7, 0.4])
    metrics = classification_metrics(actual, probability, n_bins=2)
    assert metrics.brier_score == pytest.approx(0.075)
    assert metrics.accuracy == 1.0
    table = calibration_table(probability, actual, n_bins=2)
    assert table["count"].sum() == 4

    regression = regression_metrics(np.array([1.0, 2.0]), np.array([0.0, 2.0]))
    assert regression.rmse == pytest.approx(np.sqrt(0.5))
    assert regression.mae == pytest.approx(0.5)


@pytest.mark.parametrize(
    "call",
    [
        lambda: chronological_split(20),
        lambda: expanding_window_splits(20, initial_train_size=19, test_size=2),
        lambda: fit_ridge([[1.0], [2.0]], [1.0], alpha=1.0),
        lambda: fit_lasso([[1.0], [2.0]], [1.0, 2.0], alpha=-1.0),
        lambda: fit_logistic_ridge([[1.0], [2.0]], [1.0, 1.0]),
        lambda: calibration_table([1.2], [1.0]),
    ],
)
def test_learning_helpers_reject_invalid_contracts(call) -> None:
    with pytest.raises((TypeError, ValueError)):
        call()
