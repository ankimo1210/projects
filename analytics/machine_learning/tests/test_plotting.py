"""Smoke tests for plotting helpers (Agg backend; assert they build without error)."""

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from ml_textbook import datasets, plotting  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def test_split_and_boundary_plots():
    X, y = datasets.make_moons_dataset(n=120, seed=0)
    train_idx = np.arange(0, 90)
    test_idx = np.arange(90, 120)
    assert plotting.plot_train_test_split(X, train_idx, test_idx) is not None
    clf = LogisticRegression().fit(X, y)
    assert plotting.plot_decision_boundary(clf.predict, X, y, steps=40) is not None


def test_regression_and_curves():
    x, y = datasets.make_polynomial_dataset(n=60, seed=0)
    assert plotting.plot_regression_fit(x, y) is not None
    X, yc = datasets.make_classification_dataset(n=150, n_features=4, seed=0)
    assert (
        plotting.plot_learning_curve(LogisticRegression(max_iter=500), X, yc, cv=3, n_points=4)
        is not None
    )
    assert (
        plotting.plot_validation_curve(
            LogisticRegression(max_iter=500),
            X,
            yc,
            param_name="C",
            param_range=[0.01, 0.1, 1, 10],
            cv=3,
            logx=True,
        )
        is not None
    )


def test_classification_diagnostic_plots():
    X, y = datasets.make_classification_dataset(n=300, n_features=4, seed=0)
    clf = LogisticRegression(max_iter=500).fit(X, y)
    score = clf.predict_proba(X)[:, 1]
    cm = np.array([[50, 10], [5, 35]])
    assert plotting.plot_confusion_matrix(cm, class_names=["a", "b"]) is not None
    assert plotting.plot_roc_curve(y, score) is not None
    assert plotting.plot_precision_recall_curve(y, score) is not None
    assert plotting.plot_calibration_curve(y, score, n_bins=5) is not None


def test_importance_and_unsupervised_plots():
    assert plotting.plot_feature_importance(["a", "b", "c"], [0.5, 0.2, 0.3]) is not None
    X, y = datasets.make_blobs_dataset(n=150, centers=3, seed=0)
    assert plotting.plot_pca_projection(X, y) is not None
    from sklearn.cluster import KMeans

    km = KMeans(n_clusters=3, n_init=5, random_state=0).fit(X)
    assert plotting.plot_cluster_assignments(X, km.labels_, km.cluster_centers_) is not None


def test_time_series_plots():
    assert plotting.plot_time_series_split(100, n_splits=4) is not None
    t, y = datasets.make_noisy_sine_series(n=100, seed=0)
    assert plotting.plot_forecast(t, y, y_pred=y[-20:], split_idx=80) is not None
    assert (
        plotting.plot_drift_simulation(np.arange(10), np.linspace(0.9, 0.6, 10), drift_at=5)
        is not None
    )


def test_plotly_interactives_build():
    x, y = datasets.make_polynomial_dataset(n=60, seed=0)
    fig = plotting.plotly_model_complexity(x, y, degrees=range(1, 6))
    assert len(fig.frames) == 5
    X, yc = datasets.make_classification_dataset(n=200, n_features=4, seed=0)
    clf = LogisticRegression(max_iter=500).fit(X, yc)
    fig2 = plotting.plotly_threshold_explorer(yc, clf.predict_proba(X)[:, 1], n_thresholds=9)
    assert len(fig2.frames) == 9
