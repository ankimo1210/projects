"""Interpretability helpers.

The recurring caveat of notebook 09: these tools explain **the model**, not the
world. A feature can look important because the model leans on it, even if it has
no causal effect — and correlated features make any single-feature attribution
unstable (see :func:`correlated_feature_demo`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def coefficient_table(model, feature_names) -> pd.DataFrame:
    """Tidy table of a linear model's coefficients, sorted by magnitude.

    Works on a fitted linear estimator (``.coef_``); for classifiers it uses the
    first row of ``coef_``. Columns: ``feature, coefficient, abs_coefficient``.
    """
    coef = np.asarray(model.coef_).ravel()
    df = pd.DataFrame(
        {"feature": list(feature_names), "coefficient": coef, "abs_coefficient": np.abs(coef)}
    )
    return df.sort_values("abs_coefficient", ascending=False).reset_index(drop=True)


def feature_importance_table(model, feature_names) -> pd.DataFrame:
    """Tidy table of a tree model's impurity-based ``feature_importances_``."""
    imp = np.asarray(model.feature_importances_)
    df = pd.DataFrame({"feature": list(feature_names), "importance": imp})
    return df.sort_values("importance", ascending=False).reset_index(drop=True)


def permutation_importance_table(
    estimator, X, y, n_repeats: int = 10, scoring=None, seed: int = 0
) -> pd.DataFrame:
    """Permutation importance as a tidy, sorted DataFrame.

    Measures the drop in score when each feature is shuffled — model-agnostic and
    computed on held-out data, so it reflects predictive value rather than how the
    model was built. Columns: ``feature, importance_mean, importance_std``.
    """
    from sklearn.inspection import permutation_importance

    feature_names = X.columns if isinstance(X, pd.DataFrame) else range(np.asarray(X).shape[1])
    result = permutation_importance(
        estimator, X, y, n_repeats=n_repeats, scoring=scoring, random_state=seed
    )
    df = pd.DataFrame(
        {
            "feature": list(feature_names),
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
        }
    )
    return df.sort_values("importance_mean", ascending=False).reset_index(drop=True)


def partial_dependence_values(estimator, X, feature, grid_resolution: int = 50):
    """Return ``(grid, average_prediction)`` for one feature's partial dependence.

    Partial dependence averages the model's prediction over the data while
    sweeping one feature across its range — the model's marginal view of that
    feature.
    """
    from sklearn.inspection import partial_dependence

    result = partial_dependence(
        estimator, X, [feature], grid_resolution=grid_resolution, kind="average"
    )
    return np.asarray(result["grid_values"][0]), np.asarray(result["average"][0])


def ice_curves(estimator, X, feature, grid_resolution: int = 50):
    """Return ``(grid, ice)`` Individual Conditional Expectation curves.

    ``ice`` has shape (n_instances, len(grid)): one curve per row of ``X``.
    Where ICE curves are parallel, the average (PDP) is representative; where they
    fan out, the feature's effect depends on other features (interactions).
    """
    from sklearn.inspection import partial_dependence

    result = partial_dependence(
        estimator, X, [feature], grid_resolution=grid_resolution, kind="individual"
    )
    return np.asarray(result["grid_values"][0]), np.asarray(result["individual"][0])


def correlated_feature_demo(
    n: int = 400, n_runs: int = 30, corr: float = 0.99, seed: int = 0
) -> dict:
    """Show how correlated features make coefficient attribution unstable.

    Builds two near-identical features ``x1, x2`` (correlation ``corr``) that
    *together* drive the target, fits a linear model on ``n_runs`` bootstrap
    resamples, and records each run's coefficients. The individual coefficients
    swing wildly between runs while their **sum** stays stable — the model cannot
    decide which of two interchangeable features deserves the credit.

    Returns ``{"coef_x1", "coef_x2", "coef_sum"}`` arrays of length ``n_runs``.
    """
    from sklearn.linear_model import LinearRegression

    rng = np.random.default_rng(seed)
    x1 = rng.standard_normal(n)
    x2 = corr * x1 + np.sqrt(1 - corr**2) * rng.standard_normal(n)
    # True signal uses the shared direction; individual split is arbitrary.
    y = 1.5 * x1 + 1.5 * x2 + 0.3 * rng.standard_normal(n)
    X = np.column_stack([x1, x2])

    c1, c2 = [], []
    for r in range(n_runs):
        idx = rng.integers(0, n, size=n)  # bootstrap resample
        model = LinearRegression().fit(X[idx], y[idx])
        c1.append(model.coef_[0])
        c2.append(model.coef_[1])
    c1, c2 = np.array(c1), np.array(c2)
    return {"coef_x1": c1, "coef_x2": c2, "coef_sum": c1 + c2}
