"""Tests for the end-to-end pipeline helpers."""

import numpy as np
from ml_textbook import datasets, pipelines, preprocessing
from ml_textbook.models import get_logistic_regression
from sklearn.model_selection import train_test_split


def _titanic_pipeline():
    X, y = datasets.make_titanic_like_dataset(n=600, seed=0)
    numeric, categorical = preprocessing.split_feature_types(X)
    pipe = pipelines.make_full_pipeline(numeric, categorical, get_logistic_regression())
    return X, y, pipe


def test_full_pipeline_fits_raw_dataframe():
    X, y, pipe = _titanic_pipeline()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0)
    pipe.fit(Xtr, ytr)
    acc = pipe.score(Xte, yte)
    assert acc > 0.7  # the synthetic survival signal is learnable


def test_grid_search_returns_best():
    X, y, pipe = _titanic_pipeline()
    grid = {"model__C": [0.1, 1.0, 10.0]}
    search = pipelines.grid_search(pipe, grid, X, y, cv=3)
    assert "model__C" in search.best_params_
    assert hasattr(search, "best_estimator_")


def test_save_load_roundtrip(tmp_path):
    X, y, pipe = _titanic_pipeline()
    pipe.fit(X, y)
    path = tmp_path / "pipe.joblib"
    pipelines.save_pipeline(pipe, path)
    reloaded = pipelines.load_pipeline(path)
    np.testing.assert_array_equal(
        pipelines.predict_new(pipe, X.iloc[:20]), pipelines.predict_new(reloaded, X.iloc[:20])
    )


def test_nested_cv_score_shape():
    X, y, pipe = _titanic_pipeline()
    grid = {"model__C": [0.1, 1.0]}
    scores = pipelines.nested_cv_score(pipe, grid, X, y, inner=2, outer=3)
    assert scores.shape == (3,)
    assert np.all((scores >= 0) & (scores <= 1))


def test_nested_cv_score_handles_regression():
    # Regression target must fall back to plain KFold (StratifiedKFold would raise).
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    X, y = datasets.make_regression_dataset(n=150, n_features=4, seed=0)
    pipe = Pipeline([("scale", StandardScaler()), ("model", Ridge())])
    scores = pipelines.nested_cv_score(
        pipe, {"model__alpha": [0.1, 1.0]}, X, y, inner=2, outer=3, scoring="r2"
    )
    assert scores.shape == (3,)
