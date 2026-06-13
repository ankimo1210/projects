"""Preprocessing helpers and the canonical ColumnTransformer builder.

The golden rule the whole notebook 02 is built around: **preprocessors are fit on
the training data only.** Every helper here is designed to be dropped inside a
scikit-learn ``Pipeline`` so that rule is enforced automatically by cross-validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    MinMaxScaler,
    OneHotEncoder,
    OrdinalEncoder,
    RobustScaler,
    StandardScaler,
)

_SCALERS = {
    "standard": StandardScaler,
    "minmax": MinMaxScaler,
    "robust": RobustScaler,
    "none": None,
}


# ---------------------------------------------------------------------------
# Column typing + the ColumnTransformer
# ---------------------------------------------------------------------------


def split_feature_types(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Split a DataFrame's columns into (numeric, categorical) name lists."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    # Everything non-numeric is treated as categorical. Using ``exclude`` keeps
    # this correct under the pandas 3 string dtype (object / str / category / bool).
    categorical = df.select_dtypes(exclude="number").columns.tolist()
    return numeric, categorical


def make_preprocessor(
    numeric_cols: list[str],
    categorical_cols: list[str],
    scaler: str = "standard",
) -> ColumnTransformer:
    """Build the standard tabular preprocessor as a ColumnTransformer.

    * numeric columns: median imputation -> chosen scaler
    * categorical columns: most-frequent imputation -> one-hot (unknown-safe)

    Because it is a single estimator, putting it first in a ``Pipeline`` means
    every transformer is fit on training folds only — no leakage.
    """
    scaler_cls = _SCALERS.get(scaler, StandardScaler)
    numeric_steps: list = [("impute", SimpleImputer(strategy="median"))]
    if scaler_cls is not None:
        numeric_steps.append(("scale", scaler_cls()))
    numeric_pipe = Pipeline(numeric_steps)

    categorical_pipe = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    return ColumnTransformer(
        [
            ("num", numeric_pipe, numeric_cols),
            ("cat", categorical_pipe, categorical_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


# ---------------------------------------------------------------------------
# Corruption helpers (for teaching missingness / outliers)
# ---------------------------------------------------------------------------


def inject_missing_values(
    df: pd.DataFrame, columns: list[str] | None = None, frac: float = 0.1, seed: int = 0
) -> pd.DataFrame:
    """Return a copy of ``df`` with ``frac`` of entries set to NaN (per column)."""
    rng = np.random.default_rng(seed)
    out = df.copy()
    cols = columns if columns is not None else df.columns.tolist()
    for col in cols:
        mask = rng.random(len(out)) < frac
        out.loc[mask, col] = np.nan
    return out


def inject_outliers(X, frac: float = 0.02, magnitude: float = 8.0, seed: int = 0):
    """Return a copy of array ``X`` with a fraction of rows pushed far out.

    Outliers are shifted by ``magnitude`` standard deviations in a random
    direction — useful for showing how StandardScaler (mean/std) is dragged
    around while RobustScaler (median/IQR) barely moves.
    """
    rng = np.random.default_rng(seed)
    X = np.asarray(X, dtype=float).copy()
    n = len(X)
    k = max(1, int(frac * n))
    idx = rng.choice(n, size=k, replace=False)
    shift = magnitude * X.std(axis=0) * rng.choice([-1.0, 1.0], size=(k, X.shape[1]))
    X[idx] += shift
    return X, idx


# ---------------------------------------------------------------------------
# Comparison demos
# ---------------------------------------------------------------------------


def compare_scalers(X) -> dict[str, np.ndarray]:
    """Return ``X`` transformed by each scaler (raw / standard / minmax / robust)."""
    X = np.asarray(X, dtype=float)
    return {
        "raw": X,
        "standard": StandardScaler().fit_transform(X),
        "minmax": MinMaxScaler().fit_transform(X),
        "robust": RobustScaler().fit_transform(X),
    }


def compare_encoders(values: list[str]) -> dict[str, np.ndarray]:
    """One-hot vs ordinal encoding of a single categorical column.

    Returns ``{"categories", "onehot", "ordinal"}``. The point of the demo:
    ordinal encoding invents an order (A<B<C) that a linear/distance model will
    believe, while one-hot does not.
    """
    arr = np.asarray(values, dtype=object).reshape(-1, 1)
    ohe = OneHotEncoder(sparse_output=False).fit(arr)
    ordinal = OrdinalEncoder().fit_transform(arr).ravel()
    return {
        "categories": ohe.categories_[0],
        "onehot": ohe.transform(arr),
        "ordinal": ordinal,
    }


def demo_scaling_leakage(X, test_size: float = 0.3, seed: int = 0) -> dict[str, float]:
    """Quantify the leakage from scaling before splitting.

    Fits a StandardScaler the WRONG way (on all data) and the RIGHT way (on the
    training split only), then reports the mean absolute difference in the
    *test* features between the two. A non-zero gap is the test set leaking into
    the scaler's mean/variance — invisible at fit time, real at deploy time.
    """
    from sklearn.model_selection import train_test_split

    X = np.asarray(X, dtype=float)
    X_train, X_test = train_test_split(X, test_size=test_size, random_state=seed)

    wrong = StandardScaler().fit(X)  # fit on everything (leaks test stats)
    right = StandardScaler().fit(X_train)  # fit on train only (correct)
    test_wrong = wrong.transform(X_test)
    test_right = right.transform(X_test)
    return {
        "mean_abs_diff": float(np.mean(np.abs(test_wrong - test_right))),
        "max_abs_diff": float(np.max(np.abs(test_wrong - test_right))),
    }
