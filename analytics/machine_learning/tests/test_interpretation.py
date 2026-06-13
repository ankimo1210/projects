"""Tests for interpretability helpers."""

import numpy as np
from ml_textbook import datasets, interpretation
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


def test_coefficient_table_sorted():
    X, y = datasets.make_regression_dataset(n=200, n_features=4, seed=0)
    model = LinearRegression().fit(X, y)
    table = interpretation.coefficient_table(model, ["a", "b", "c", "d"])
    assert list(table.columns) == ["feature", "coefficient", "abs_coefficient"]
    # Sorted by absolute magnitude, descending.
    assert table["abs_coefficient"].is_monotonic_decreasing


def test_feature_importance_table():
    X, y = datasets.make_regression_dataset(n=200, n_features=4, seed=0)
    model = RandomForestRegressor(n_estimators=20, random_state=0).fit(X, y)
    table = interpretation.feature_importance_table(model, ["a", "b", "c", "d"])
    assert table["importance"].sum() > 0
    assert table["importance"].is_monotonic_decreasing


def test_permutation_importance_table():
    X, y = datasets.make_regression_dataset(n=200, n_features=4, seed=0)
    model = RandomForestRegressor(n_estimators=20, random_state=0).fit(X, y)
    table = interpretation.permutation_importance_table(model, X, y, n_repeats=5, seed=0)
    assert list(table.columns) == ["feature", "importance_mean", "importance_std"]
    assert len(table) == 4


def test_partial_dependence_and_ice():
    X, y = datasets.make_regression_dataset(n=200, n_features=3, seed=0)
    model = RandomForestRegressor(n_estimators=20, random_state=0).fit(X, y)
    grid, avg = interpretation.partial_dependence_values(model, X, 0, grid_resolution=20)
    assert grid.shape == avg.shape == (20,)
    grid2, ice = interpretation.ice_curves(model, X, 0, grid_resolution=20)
    assert ice.shape == (200, 20)


def test_correlated_feature_demo_shows_instability():
    out = interpretation.correlated_feature_demo(n=400, n_runs=40, corr=0.99, seed=0)
    # Each coefficient is far more variable than their (stable) sum.
    assert out["coef_x1"].std() > out["coef_sum"].std()
    assert out["coef_x2"].std() > out["coef_sum"].std()
