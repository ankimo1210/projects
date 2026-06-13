"""Tests for model factories and the educational GD linear regressor."""

import numpy as np
import pytest
from ml_textbook import datasets, models
from sklearn.linear_model import LinearRegression


def test_factories_fit_and_predict():
    X, y = datasets.make_classification_dataset(n=200, n_features=4, seed=0)
    for factory in (
        models.get_logistic_regression,
        models.get_decision_tree,
        models.get_random_forest,
        models.get_gradient_boosting,
        models.get_hist_gradient_boosting,
        models.get_svc,
    ):
        clf = factory()
        clf.fit(X, y)
        pred = clf.predict(X)
        assert pred.shape == (200,)
        assert clf.score(X, y) > 0.7  # learns the easy synthetic signal


def test_regression_factories():
    X, y = datasets.make_regression_dataset(n=200, n_features=5, seed=0)
    for factory in (
        models.get_linear_regression,
        models.get_ridge,
        models.get_lasso,
        models.get_elastic_net,
    ):
        reg = factory()
        reg.fit(X, y)
        assert reg.predict(X).shape == (200,)


def test_get_model_registry():
    clf = models.get_model("forest", n_estimators=10)
    assert clf.n_estimators == 10
    with pytest.raises(KeyError):
        models.get_model("does_not_exist")


def test_gd_linear_regressor_descends_and_matches_ols():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, 3))
    true_w = np.array([2.0, -1.0, 0.5])
    y = X @ true_w + 0.1 * rng.normal(size=300)

    gd = models.GDLinearRegressor(lr=0.1, epochs=500).fit(X, y)
    # Loss is monotone-ish: the end is far below the start.
    assert gd.loss_history_[-1] < gd.loss_history_[0] * 0.1
    # Converges close to the closed-form OLS solution.
    ols = LinearRegression().fit(X, y)
    np.testing.assert_allclose(gd.w_, ols.coef_, atol=0.05)
