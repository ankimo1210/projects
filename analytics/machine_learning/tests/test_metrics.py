"""Tests for metrics — from-scratch implementations checked against scikit-learn."""

import numpy as np
import pytest
from ml_textbook import metrics
from sklearn import metrics as skm


@pytest.fixture
def reg_data():
    rng = np.random.default_rng(0)
    y_true = rng.normal(size=200)
    y_pred = y_true + 0.3 * rng.normal(size=200)
    return y_true, y_pred


@pytest.fixture
def clf_data():
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=300)
    score = np.clip(0.5 + 0.4 * (y_true - 0.5) + 0.2 * rng.normal(size=300), 0, 1)
    y_pred = (score >= 0.5).astype(int)
    return y_true, y_pred, score


def test_regression_metrics_match_sklearn(reg_data):
    y_true, y_pred = reg_data
    assert metrics.mse(y_true, y_pred) == pytest.approx(skm.mean_squared_error(y_true, y_pred))
    assert metrics.mae(y_true, y_pred) == pytest.approx(skm.mean_absolute_error(y_true, y_pred))
    assert metrics.r2_score(y_true, y_pred) == pytest.approx(skm.r2_score(y_true, y_pred))
    assert metrics.rmse(y_true, y_pred) == pytest.approx(
        np.sqrt(skm.mean_squared_error(y_true, y_pred))
    )


def test_classification_metrics_match_sklearn(clf_data):
    y_true, y_pred, _ = clf_data
    assert metrics.accuracy(y_true, y_pred) == pytest.approx(skm.accuracy_score(y_true, y_pred))
    assert metrics.precision(y_true, y_pred) == pytest.approx(skm.precision_score(y_true, y_pred))
    assert metrics.recall(y_true, y_pred) == pytest.approx(skm.recall_score(y_true, y_pred))
    assert metrics.f1_score(y_true, y_pred) == pytest.approx(skm.f1_score(y_true, y_pred))


def test_confusion_matrix_matches_sklearn(clf_data):
    y_true, y_pred, _ = clf_data
    np.testing.assert_array_equal(
        metrics.confusion_matrix(y_true, y_pred, n_classes=2), skm.confusion_matrix(y_true, y_pred)
    )


def test_ranking_metrics_match_sklearn(clf_data):
    y_true, _, score = clf_data
    assert metrics.roc_auc(y_true, score) == pytest.approx(skm.roc_auc_score(y_true, score))
    assert metrics.pr_auc(y_true, score) == pytest.approx(
        skm.average_precision_score(y_true, score)
    )


def test_ece_is_low_for_calibrated_and_high_for_skewed():
    rng = np.random.default_rng(0)
    # Perfectly calibrated: label drawn with probability == predicted prob.
    p = rng.uniform(0, 1, size=5000)
    y = (rng.uniform(size=5000) < p).astype(int)
    ece_good = metrics.expected_calibration_error(y, p, n_bins=10)
    # Badly miscalibrated: always predict 0.99 but only half are positive.
    ece_bad = metrics.expected_calibration_error(y, np.full(5000, 0.99), n_bins=10)
    assert ece_good < 0.05
    assert ece_bad > 0.3
