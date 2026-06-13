"""Smoke tests for ipywidgets demos.

``interact`` calls the inner ``draw`` once on creation, so calling each explorer
exercises its plotting/model logic even without a live frontend. We only assert
construction succeeds (with the Agg backend so nothing tries to render).
"""

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from ml_textbook import datasets, widgets  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def test_classification_explorers_build():
    X, y = datasets.make_moons_dataset(n=120, seed=0)
    assert widgets.model_complexity_explorer(X, y) is not None
    assert widgets.decision_tree_depth_explorer(X, y) is not None
    assert widgets.random_forest_size_explorer(X, y) is not None
    assert widgets.svm_explorer(X, y) is not None
    assert widgets.drift_severity_explorer(X, y) is not None


def test_regression_and_reg_strength_explorers_build():
    x, y = datasets.make_polynomial_dataset(n=60, seed=0)
    assert widgets.polynomial_degree_explorer(x, y) is not None
    X, yr = datasets.make_regression_dataset(n=150, n_features=6, seed=0)
    assert widgets.regularization_strength_explorer(X, yr) is not None


def test_threshold_explorer_builds():
    X, y = datasets.make_classification_dataset(n=200, n_features=4, seed=0)
    clf = LogisticRegression(max_iter=500).fit(X, y)
    score = clf.predict_proba(X)[:, 1]
    assert widgets.classification_threshold_explorer(y, score) is not None


def test_unsupervised_and_timeseries_explorers_build():
    X, _ = datasets.make_blobs_dataset(n=150, centers=3, seed=0)
    assert widgets.kmeans_explorer(X) is not None
    Xd = datasets.load_digits_dataset().data.to_numpy()[:200]
    assert widgets.pca_components_explorer(Xd) is not None
    assert widgets.rolling_validation_explorer(n_samples=80) is not None
