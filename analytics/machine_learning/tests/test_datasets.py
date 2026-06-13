"""Tests for dataset loaders and generators (shapes, reproducibility, properties)."""

import numpy as np
import pandas as pd
import pytest
from ml_textbook import datasets


def test_sklearn_loaders_shapes():
    assert datasets.load_iris_dataset().data.shape == (150, 4)
    assert datasets.load_wine_dataset().data.shape == (178, 13)
    assert datasets.load_breast_cancer_dataset().data.shape == (569, 30)
    assert datasets.load_diabetes_dataset().data.shape == (442, 10)
    assert datasets.load_digits_dataset().data.shape == (1797, 64)


def test_california_housing_or_skip():
    try:
        bunch = datasets.load_california_housing_dataset()
    except Exception as exc:  # network unavailable on first fetch
        pytest.skip(f"california housing fetch failed (offline?): {exc}")
    assert bunch.data.shape[1] == 8
    assert len(bunch.target) == bunch.data.shape[0]


def test_make_regression_and_classification_shapes():
    X, y = datasets.make_regression_dataset(n=120, n_features=3, seed=0)
    assert X.shape == (120, 3) and y.shape == (120,)
    X, y = datasets.make_classification_dataset(n=200, n_features=2, n_classes=2, seed=0)
    assert X.shape == (200, 2)
    assert set(np.unique(y)) == {0, 1}


def test_imbalanced_ratio():
    _, y = datasets.make_imbalanced_classification_dataset(n=2000, weights=(0.95, 0.05), seed=0)
    pos_rate = y.mean()
    assert 0.02 < pos_rate < 0.10  # roughly 5% positives


def test_2d_shape_datasets():
    for maker in (datasets.make_moons_dataset, datasets.make_circles_dataset):
        X, y = maker(n=300, seed=1)
        assert X.shape == (300, 2)
        assert set(np.unique(y)) == {0, 1}
    X, y = datasets.make_blobs_dataset(n=300, centers=4, seed=1)
    assert X.shape == (300, 2)
    assert len(np.unique(y)) == 4


def test_reproducible_seeds():
    a, _ = datasets.make_moons_dataset(n=100, seed=7)
    b, _ = datasets.make_moons_dataset(n=100, seed=7)
    np.testing.assert_array_equal(a, b)
    c, _ = datasets.make_moons_dataset(n=100, seed=8)
    assert not np.array_equal(a, c)


def test_titanic_like_structure():
    X, y = datasets.make_titanic_like_dataset(n=500, seed=0)
    assert isinstance(X, pd.DataFrame)
    assert list(X.columns) == ["pclass", "sex", "age", "sibsp", "parch", "fare", "embarked"]
    assert len(X) == len(y) == 500
    assert set(np.unique(y)) <= {0, 1}
    # Mixed types and injected missingness (sex is a string column, not numeric).
    assert not pd.api.types.is_numeric_dtype(X["sex"])
    assert X["age"].isna().sum() > 0
    # Women survive more often than men (the signal we built in).
    rate_f = y[X["sex"] == "female"].mean()
    rate_m = y[X["sex"] == "male"].mean()
    assert rate_f > rate_m


def test_time_series_generators():
    t, y = datasets.make_time_series_trend_seasonality(n=200, seed=0)
    assert t.shape == (200,) and y.shape == (200,)
    # Upward trend: second half mean exceeds first half mean.
    assert y[100:].mean() > y[:100].mean()

    t, y = datasets.make_noisy_sine_series(n=150, seed=0)
    assert y.shape == (150,)

    y = datasets.make_ar_process(n=300, seed=0)
    assert y.shape == (300,) and np.isfinite(y).all()

    y, regime = datasets.make_regime_switching_series(n=400, seed=0)
    assert y.shape == (400,) and set(np.unique(regime)) <= {0, 1}


def test_anomaly_dataset():
    X, y = datasets.make_anomaly_dataset(n_normal=200, n_anomalies=10, seed=0)
    assert X.shape == (210, 2)
    assert y.sum() == 10  # exactly the planted anomalies


def test_train_validation_test_split_partition():
    X = np.arange(1000).reshape(-1, 1)
    y = np.arange(1000) % 2
    Xtr, Xval, Xte, ytr, yval, yte = datasets.train_validation_test_split(
        X, y, val_size=0.2, test_size=0.2, stratify=True, seed=0
    )
    assert len(Xte) == 200
    assert len(Xval) == 200
    assert len(Xtr) == 600
    # Disjoint and covering.
    all_idx = set(Xtr.ravel()) | set(Xval.ravel()) | set(Xte.ravel())
    assert all_idx == set(range(1000))
