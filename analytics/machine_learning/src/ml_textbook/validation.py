"""Validation helpers: splits, cross-validation, time-aware validation, leakage checks.

The thin wrappers around scikit-learn keep a single import surface for the
notebooks; the from-scratch fold generator and the walk-forward loop are written
out so the *ordering* of train/test data — the thing that matters most for honest
evaluation — is explicit and inspectable.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
from sklearn.base import clone
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    TimeSeriesSplit,
    cross_val_score,
    train_test_split,
)

# ---------------------------------------------------------------------------
# Basic splits
# ---------------------------------------------------------------------------


def simple_train_test_split(X, y, test_size: float = 0.25, seed: int = 0):
    """Plain random split. Returns (X_train, X_test, y_train, y_test)."""
    return train_test_split(X, y, test_size=test_size, random_state=seed)


def stratified_train_test_split(X, y, test_size: float = 0.25, seed: int = 0):
    """Random split that preserves class proportions. Returns 4 arrays."""
    return train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)


# ---------------------------------------------------------------------------
# Cross-validation fold generators
# ---------------------------------------------------------------------------


def kfold_indices(n_samples: int, n_splits: int = 5, shuffle: bool = True, seed: int = 0):
    """Yield ``(train_idx, test_idx)`` for plain k-fold CV (scikit-learn under the hood)."""
    kf = KFold(n_splits=n_splits, shuffle=shuffle, random_state=seed if shuffle else None)
    return list(kf.split(np.zeros(n_samples)))


def stratified_kfold_indices(y, n_splits: int = 5, shuffle: bool = True, seed: int = 0):
    """Yield ``(train_idx, test_idx)`` for stratified k-fold CV (preserves class ratios)."""
    skf = StratifiedKFold(
        n_splits=n_splits, shuffle=shuffle, random_state=seed if shuffle else None
    )
    return list(skf.split(np.zeros(len(y)), y))


def cross_validate_scores(
    estimator, X, y, n_splits: int = 5, scoring=None, stratified: bool = True
):
    """Return the per-fold cross-validation scores as a NumPy array.

    Uses stratified folds for classification by default; pass ``stratified=False``
    for plain k-fold (e.g. regression).
    """
    cv = (
        StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=0)
        if stratified
        else KFold(n_splits=n_splits, shuffle=True, random_state=0)
    )
    return cross_val_score(estimator, X, y, cv=cv, scoring=scoring)


# ---------------------------------------------------------------------------
# Time-aware validation
# ---------------------------------------------------------------------------


def time_series_split_indices(n_samples: int, n_splits: int = 5):
    """Yield ``(train_idx, test_idx)`` for forward-chaining time-series CV.

    Every test fold lies strictly *after* its training fold in time, so no future
    information leaks backwards. Wraps :class:`sklearn.model_selection.TimeSeriesSplit`.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    return list(tscv.split(np.zeros(n_samples)))


def walk_forward_validation(
    estimator,
    X,
    y,
    initial: int,
    horizon: int = 1,
    step: int | None = None,
    expanding: bool = True,
    metric=None,
) -> Iterator[dict]:
    """Walk-forward (a.k.a. backtest) validation for ordered data.

    Repeatedly fit on the past and predict the next ``horizon`` steps, marching
    forward. With ``expanding=True`` the training window grows from the start;
    with ``expanding=False`` it is a fixed-width rolling window of length
    ``initial``.

    Parameters
    ----------
    estimator : a scikit-learn regressor/classifier (cloned + refit each fold).
    X, y : array-likes already sorted in time order.
    initial : size of the first training window.
    horizon : number of steps predicted per fold.
    step : how far to advance each fold (defaults to ``horizon``).
    metric : ``metric(y_true, y_pred) -> float``; if given, each yielded record
        carries a ``"score"``.

    Yields one dict per fold with ``train_start/train_end/test_start/test_end``,
    ``y_true``, ``y_pred`` and (optionally) ``score``.
    """
    X = np.asarray(X)
    y = np.asarray(y)
    n = len(X)
    step = horizon if step is None else step
    start = initial
    while start + horizon <= n:
        train_start = 0 if expanding else max(0, start - initial)
        tr = slice(train_start, start)
        te = slice(start, start + horizon)
        model = clone(estimator)
        model.fit(X[tr], y[tr])
        y_pred = model.predict(X[te])
        record = {
            "train_start": train_start,
            "train_end": start,
            "test_start": start,
            "test_end": start + horizon,
            "y_true": y[te],
            "y_pred": y_pred,
        }
        if metric is not None:
            record["score"] = float(metric(y[te], y_pred))
        yield record
        start += step


# ---------------------------------------------------------------------------
# Leakage checks
# ---------------------------------------------------------------------------


def assert_disjoint_indices(train_idx, test_idx) -> None:
    """Raise if train and test index sets overlap (a basic leakage guard)."""
    overlap = set(np.asarray(train_idx).tolist()) & set(np.asarray(test_idx).tolist())
    if overlap:
        raise AssertionError(f"train/test indices overlap on {len(overlap)} samples")


def find_leaky_features(X, y, threshold: float = 0.98) -> list:
    """Flag columns whose absolute correlation with the target is suspiciously high.

    A feature that is near-perfectly correlated with the target is almost always
    leakage (e.g. an id that encodes the label, or a post-outcome measurement).
    Works on a DataFrame (returns column names) or a 2-D array (returns indices).
    """
    import pandas as pd

    y = np.asarray(y, dtype=float)
    suspects = []
    if isinstance(X, pd.DataFrame):
        for col in X.columns:
            xc = pd.to_numeric(X[col], errors="coerce").to_numpy(dtype=float)
            if np.std(xc[~np.isnan(xc)]) == 0:
                continue
            r = _safe_corr(xc, y)
            if abs(r) >= threshold:
                suspects.append(col)
    else:
        X = np.asarray(X, dtype=float)
        for j in range(X.shape[1]):
            if np.std(X[:, j]) == 0:
                continue
            r = _safe_corr(X[:, j], y)
            if abs(r) >= threshold:
                suspects.append(j)
    return suspects


def _safe_corr(x, y) -> float:
    mask = ~np.isnan(x) & ~np.isnan(y)
    if mask.sum() < 2:
        return 0.0
    return float(np.corrcoef(x[mask], y[mask])[0, 1])
