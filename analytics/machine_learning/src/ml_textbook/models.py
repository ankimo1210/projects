"""Model factories.

Thin, well-named constructors for the scikit-learn estimators used across the
book (so notebooks read like prose and hyper-parameters have one obvious home),
plus one tiny from-scratch gradient-descent linear regressor used to make the
"models are just loss minimisation" point concrete in notebooks 01 and 03.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import (
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import (
    ElasticNet,
    Lasso,
    LinearRegression,
    LogisticRegression,
    Ridge,
)
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

# ---------------------------------------------------------------------------
# Linear models
# ---------------------------------------------------------------------------


def get_linear_regression():
    """Ordinary least squares."""
    return LinearRegression()


def get_ridge(alpha: float = 1.0):
    """L2-penalised regression (shrinks coefficients toward 0, keeps all of them)."""
    return Ridge(alpha=alpha)


def get_lasso(alpha: float = 0.1):
    """L1-penalised regression (drives some coefficients exactly to 0: selection)."""
    return Lasso(alpha=alpha, max_iter=10000)


def get_elastic_net(alpha: float = 0.1, l1_ratio: float = 0.5):
    """Mix of L1 and L2 penalties (``l1_ratio`` blends lasso and ridge)."""
    return ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=10000)


def get_logistic_regression(C: float = 1.0, max_iter: int = 1000):
    """Linear classifier with a log-loss objective. ``C`` is inverse regularisation."""
    return LogisticRegression(C=C, max_iter=max_iter)


# ---------------------------------------------------------------------------
# Tree-based models
# ---------------------------------------------------------------------------


def get_decision_tree(max_depth: int | None = None, criterion: str = "gini", seed: int = 0):
    """A single classification tree (interpretable but high-variance)."""
    return DecisionTreeClassifier(max_depth=max_depth, criterion=criterion, random_state=seed)


def get_decision_tree_regressor(max_depth: int | None = None, seed: int = 0):
    """A single regression tree (piecewise-constant predictions)."""
    return DecisionTreeRegressor(max_depth=max_depth, random_state=seed)


def get_random_forest(n_estimators: int = 200, max_depth: int | None = None, seed: int = 0):
    """Bagged trees on bootstrap samples + random feature subsets (variance down)."""
    return RandomForestClassifier(
        n_estimators=n_estimators, max_depth=max_depth, random_state=seed, n_jobs=-1
    )


def get_random_forest_regressor(
    n_estimators: int = 200, max_depth: int | None = None, seed: int = 0
):
    """Random-forest regressor."""
    return RandomForestRegressor(
        n_estimators=n_estimators, max_depth=max_depth, random_state=seed, n_jobs=-1
    )


def get_gradient_boosting(n_estimators: int = 100, learning_rate: float = 0.1, seed: int = 0):
    """Trees fit sequentially to the residual errors of the ensemble so far."""
    return GradientBoostingClassifier(
        n_estimators=n_estimators, learning_rate=learning_rate, random_state=seed
    )


def get_hist_gradient_boosting(learning_rate: float = 0.1, max_iter: int = 200, seed: int = 0):
    """Histogram-based gradient boosting (fast; the scikit-learn 'XGBoost-like')."""
    return HistGradientBoostingClassifier(
        learning_rate=learning_rate, max_iter=max_iter, random_state=seed
    )


# ---------------------------------------------------------------------------
# SVM
# ---------------------------------------------------------------------------


def get_svc(
    C: float = 1.0, kernel: str = "rbf", gamma: str | float = "scale", probability: bool = False
):
    """Support-vector classifier. ``C`` = soft-margin penalty, ``gamma`` = RBF width."""
    return SVC(C=C, kernel=kernel, gamma=gamma, probability=probability, random_state=0)


# ---------------------------------------------------------------------------
# Registry (used by widgets / generic demos)
# ---------------------------------------------------------------------------

MODEL_REGISTRY = {
    "logistic": get_logistic_regression,
    "tree": get_decision_tree,
    "forest": get_random_forest,
    "gboost": get_gradient_boosting,
    "histgboost": get_hist_gradient_boosting,
    "svc": get_svc,
}


def get_model(name: str, **kwargs):
    """Look up a classifier factory by name and build it with ``kwargs``."""
    if name not in MODEL_REGISTRY:
        raise KeyError(f"unknown model '{name}'; choices: {sorted(MODEL_REGISTRY)}")
    return MODEL_REGISTRY[name](**kwargs)


# ---------------------------------------------------------------------------
# From-scratch gradient-descent linear regression (educational)
# ---------------------------------------------------------------------------


class GDLinearRegressor:
    """Least-squares linear regression trained by batch gradient descent.

    Exists only to make the optimisation visible: ``loss_history_`` records the
    MSE at every epoch so notebooks can plot the descent. For real work use
    :func:`get_linear_regression` (closed-form OLS). Standardise features first;
    gradient descent is scale-sensitive.

    Fits ``y ~ X @ w + b`` by minimising mean squared error.
    """

    def __init__(self, lr: float = 0.1, epochs: int = 200):
        self.lr = lr
        self.epochs = epochs
        self.w_ = None
        self.b_ = 0.0
        self.loss_history_: list[float] = []

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        self.w_ = np.zeros(d)
        self.b_ = 0.0
        self.loss_history_ = []
        for _ in range(self.epochs):
            pred = X @ self.w_ + self.b_
            err = pred - y
            self.loss_history_.append(float(np.mean(err**2)))
            grad_w = (2.0 / n) * (X.T @ err)
            grad_b = (2.0 / n) * np.sum(err)
            self.w_ -= self.lr * grad_w
            self.b_ -= self.lr * grad_b
        return self

    def predict(self, X):
        return np.asarray(X, dtype=float) @ self.w_ + self.b_
