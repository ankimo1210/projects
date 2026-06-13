"""Tests for preprocessing helpers and the ColumnTransformer."""

import numpy as np
import pandas as pd
from ml_textbook import datasets, preprocessing


def test_split_feature_types_on_titanic():
    X, _ = datasets.make_titanic_like_dataset(n=200, seed=0)
    numeric, categorical = preprocessing.split_feature_types(X)
    assert "age" in numeric and "fare" in numeric
    assert "sex" in categorical and "embarked" in categorical


def test_make_preprocessor_handles_missing_and_categoricals():
    X, _ = datasets.make_titanic_like_dataset(n=300, seed=0)
    numeric, categorical = preprocessing.split_feature_types(X)
    pre = preprocessing.make_preprocessor(numeric, categorical)
    Z = pre.fit_transform(X)
    assert Z.shape[0] == len(X)
    assert not np.isnan(Z).any()  # imputation removed all NaNs
    # One-hot expanded the categoricals beyond the raw column count.
    assert Z.shape[1] > len(numeric)


def test_onehot_handles_unknown_categories():
    X, _ = datasets.make_titanic_like_dataset(n=200, seed=0)
    numeric, categorical = preprocessing.split_feature_types(X)
    pre = preprocessing.make_preprocessor(numeric, categorical).fit(X)
    novel = X.iloc[:5].copy()
    novel.loc[novel.index, "embarked"] = "Z"  # category never seen in fit
    Z = pre.transform(novel)  # must not raise
    assert Z.shape[0] == 5


def test_compare_scalers_standardizes():
    X, _ = datasets.make_blobs_dataset(n=300, seed=0)
    scaled = preprocessing.compare_scalers(X)
    assert np.allclose(scaled["standard"].mean(axis=0), 0, atol=1e-6)
    assert np.allclose(scaled["standard"].std(axis=0), 1, atol=1e-6)
    assert scaled["minmax"].min() >= -1e-9 and scaled["minmax"].max() <= 1 + 1e-9


def test_inject_missing_values():
    X, _ = datasets.make_titanic_like_dataset(n=200, seed=0)
    corrupted = preprocessing.inject_missing_values(X, columns=["fare"], frac=0.3, seed=0)
    assert corrupted["fare"].isna().sum() > X["fare"].isna().sum()


def test_inject_outliers_moves_points():
    X, _ = datasets.make_blobs_dataset(n=200, seed=0)
    Xo, idx = preprocessing.inject_outliers(X, frac=0.05, magnitude=10.0, seed=0)
    assert len(idx) >= 1
    # The outliers inflate the spread substantially.
    assert Xo.std() > X.std()


def test_demo_scaling_leakage_detects_contamination():
    X, _ = datasets.make_blobs_dataset(n=200, seed=0)
    result = preprocessing.demo_scaling_leakage(X, test_size=0.3, seed=0)
    assert result["mean_abs_diff"] > 0  # fitting on all data leaks test stats


def test_compare_encoders():
    out = preprocessing.compare_encoders(["A", "B", "C", "A"])
    assert out["onehot"].shape == (4, 3)
    assert out["ordinal"].shape == (4,)
    assert list(out["categories"]) == ["A", "B", "C"]
