"""Tests for validation helpers (folds, time-aware splits, leakage checks)."""

import numpy as np
import pandas as pd
import pytest
from ml_textbook import datasets, validation
from sklearn.linear_model import LinearRegression


def test_kfold_indices_disjoint_and_cover():
    folds = validation.kfold_indices(100, n_splits=5, seed=0)
    assert len(folds) == 5
    for tr, te in folds:
        validation.assert_disjoint_indices(tr, te)
        assert len(tr) + len(te) == 100
    # Every sample is a test point exactly once.
    test_union = np.concatenate([te for _, te in folds])
    assert sorted(test_union) == list(range(100))


def test_stratified_kfold_preserves_ratio():
    y = np.array([0] * 90 + [1] * 10)
    folds = validation.stratified_kfold_indices(y, n_splits=5, seed=0)
    for _, te in folds:
        # Each test fold keeps ~10% positives (2 of 20).
        assert y[te].mean() == pytest.approx(0.1, abs=0.06)


def test_time_series_split_is_forward_only():
    folds = validation.time_series_split_indices(100, n_splits=4)
    for tr, te in folds:
        assert max(tr) < min(te)  # train strictly before test


def test_walk_forward_windows_and_scores():
    y = datasets.make_ar_process(n=120, seed=0)
    X = np.arange(120).reshape(-1, 1).astype(float)
    records = list(
        validation.walk_forward_validation(
            LinearRegression(),
            X,
            y,
            initial=60,
            horizon=10,
            expanding=True,
            metric=lambda a, b: float(np.mean((a - b) ** 2)),
        )
    )
    assert len(records) == 6  # (120-60)/10
    first = records[0]
    assert first["train_start"] == 0 and first["train_end"] == 60
    assert first["test_start"] == 60 and first["test_end"] == 70
    assert "score" in first
    # Rolling window keeps a fixed training size.
    roll = list(
        validation.walk_forward_validation(
            LinearRegression(), X, y, initial=40, horizon=20, expanding=False
        )
    )
    assert roll[1]["train_end"] - roll[1]["train_start"] == 40


def test_find_leaky_features():
    X, y = datasets.make_classification_dataset(n=300, n_features=3, seed=0)
    df = pd.DataFrame(X, columns=["a", "b", "c"])
    df["leak"] = y + 0.001 * np.random.default_rng(0).normal(size=len(y))  # near-perfect copy
    suspects = validation.find_leaky_features(df, y, threshold=0.95)
    assert "leak" in suspects
    assert "a" not in suspects


def test_assert_disjoint_raises_on_overlap():
    with pytest.raises(AssertionError):
        validation.assert_disjoint_indices([1, 2, 3], [3, 4, 5])


def test_cross_validate_scores_handles_regression():
    # Continuous target must NOT trigger StratifiedKFold (it would raise).
    X, y = datasets.make_regression_dataset(n=120, n_features=3, seed=0)
    scores = validation.cross_validate_scores(LinearRegression(), X, y, n_splits=4, scoring="r2")
    assert scores.shape == (4,)
