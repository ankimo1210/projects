"""Datasets for the machine-learning textbook.

Two sources only, both safe for a normal laptop:

* **scikit-learn loaders** — Iris / Wine / Breast Cancer / Diabetes / Digits are
  bundled with scikit-learn (no download). California Housing is fetched once and
  cached by scikit-learn under ``~/scikit_learn_data``.
* **local synthetic generators** — everything else is generated with a fixed seed
  via ``numpy.random.default_rng`` so results are reproducible and offline.

scikit-learn loaders return the familiar :class:`sklearn.utils.Bunch` (with
``.data`` as a DataFrame, ``.target`` as a Series, plus ``.feature_names`` /
``.target_names``). Synthetic generators return plain NumPy arrays, except
:func:`make_titanic_like_dataset` which returns a mixed-type DataFrame.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.datasets import (
    fetch_california_housing,
    load_breast_cancer,
    load_diabetes,
    load_digits,
    load_iris,
    load_wine,
    make_blobs,
    make_circles,
    make_classification,
    make_moons,
    make_regression,
)
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# Bundled scikit-learn datasets (as pandas frames, with names attached)
# ---------------------------------------------------------------------------


def load_iris_dataset():
    """Iris (150 x 4, 3 balanced flower classes). Returns an sklearn Bunch."""
    return load_iris(as_frame=True)


def load_wine_dataset():
    """Wine (178 x 13, 3 cultivar classes). Returns an sklearn Bunch."""
    return load_wine(as_frame=True)


def load_breast_cancer_dataset():
    """Breast Cancer Wisconsin (569 x 30, binary malignant/benign). Bunch."""
    return load_breast_cancer(as_frame=True)


def load_diabetes_dataset():
    """Diabetes regression (442 x 10, target = disease progression). Bunch."""
    return load_diabetes(as_frame=True)


def load_digits_dataset():
    """Handwritten digits (1797 x 64, 10 classes of 8x8 images). Bunch.

    The Bunch also carries ``.images`` of shape (n, 8, 8) for plotting.
    """
    return load_digits(as_frame=True)


def load_california_housing_dataset():
    """California Housing regression (20640 x 8, target = median house value).

    Fetched once from the scikit-learn mirror and then cached locally; needs
    network access only on the very first call. Returns an sklearn Bunch.
    """
    return fetch_california_housing(as_frame=True)


# ---------------------------------------------------------------------------
# Synthetic supervised datasets
# ---------------------------------------------------------------------------


def make_regression_dataset(
    n: int = 200,
    n_features: int = 1,
    n_informative: int | None = None,
    noise: float = 15.0,
    seed: int = 0,
):
    """Linear-with-noise regression. Returns (X[n, n_features], y[n]) float64."""
    if n_informative is None:
        n_informative = n_features
    X, y = make_regression(
        n_samples=n,
        n_features=n_features,
        n_informative=n_informative,
        noise=noise,
        random_state=seed,
    )
    return X, y


def make_polynomial_dataset(n: int = 80, degree: int = 3, noise: float = 0.3, seed: int = 0):
    """1-D data from a fixed cubic curve plus noise. Returns (x[n, 1], y[n]).

    Handy for the polynomial / under- vs over-fitting demos: the *true* function
    is a degree-3 polynomial, so fitting much higher degrees overfits.
    """
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(-3.0, 3.0, n))
    true = 0.5 * x**3 - x**2 - 2 * x + 1
    y = true + noise * np.std(true) * rng.standard_normal(n)
    return x[:, None], y


def make_classification_dataset(
    n: int = 300,
    n_features: int = 2,
    n_classes: int = 2,
    class_sep: float = 1.2,
    seed: int = 0,
):
    """Gaussian-cluster classification. Returns (X[n, n_features], y[n]).

    With ``n_features=2`` the data is fully visualizable (no redundant features),
    which is what the decision-boundary demos use.
    """
    n_informative = n_features if n_features <= 2 else max(2, n_features // 2)
    X, y = make_classification(
        n_samples=n,
        n_features=n_features,
        n_informative=n_informative,
        n_redundant=0,
        n_repeated=0,
        n_classes=n_classes,
        n_clusters_per_class=1,
        class_sep=class_sep,
        random_state=seed,
    )
    return X, y.astype(np.int64)


def make_imbalanced_classification_dataset(
    n: int = 2000, weights: tuple[float, float] = (0.95, 0.05), seed: int = 0
):
    """Binary classification with a rare positive class. Returns (X[n, 2], y[n]).

    The default 95/5 split makes accuracy a misleading metric (the constant
    'always negative' classifier already scores 0.95) — the running example for
    precision/recall/PR-AUC in the evaluation notebook.
    """
    X, y = make_classification(
        n_samples=n,
        n_features=2,
        n_informative=2,
        n_redundant=0,
        n_repeated=0,
        n_classes=2,
        n_clusters_per_class=1,
        weights=list(weights),
        class_sep=1.0,
        random_state=seed,
    )
    return X, y.astype(np.int64)


def make_blobs_dataset(n: int = 400, centers: int = 3, cluster_std: float = 1.0, seed: int = 0):
    """Isotropic Gaussian blobs. Returns (X[n, 2], y[n]); y is the blob id."""
    X, y = make_blobs(n_samples=n, centers=centers, cluster_std=cluster_std, random_state=seed)
    return X, y.astype(np.int64)


def make_moons_dataset(n: int = 400, noise: float = 0.2, seed: int = 0):
    """Two interleaving half-moons (not linearly separable). Returns (X[n,2], y)."""
    X, y = make_moons(n_samples=n, noise=noise, random_state=seed)
    return X, y.astype(np.int64)


def make_circles_dataset(n: int = 400, noise: float = 0.1, factor: float = 0.5, seed: int = 0):
    """Concentric circles (inner vs outer ring). Returns (X[n, 2], y[n])."""
    X, y = make_circles(n_samples=n, noise=noise, factor=factor, random_state=seed)
    return X, y.astype(np.int64)


# ---------------------------------------------------------------------------
# Titanic-like tabular dataset (mixed types + missing values, fully synthetic)
# ---------------------------------------------------------------------------


def make_titanic_like_dataset(n: int = 891, seed: int = 0):
    """A robust, fully synthetic Titanic-style dataset (no external download).

    Mimics the real Titanic's flavour — mixed numeric / categorical columns,
    missing values in ``age`` / ``embarked``, a ``fare`` that tracks passenger
    class, and survival driven mostly by sex and class. Built for the
    preprocessing (02) and end-to-end pipeline (10) notebooks.

    Returns ``(X, y)`` where ``X`` is a DataFrame with columns
    ``[pclass, sex, age, sibsp, parch, fare, embarked]`` and ``y`` is a 0/1
    ``survived`` Series.
    """
    rng = np.random.default_rng(seed)

    pclass = rng.choice([1, 2, 3], size=n, p=[0.24, 0.21, 0.55])
    sex = rng.choice(["female", "male"], size=n, p=[0.35, 0.65])
    age = np.clip(rng.normal(29.0, 14.0, n), 0.4, 80.0)
    sibsp = rng.poisson(0.5, n)
    parch = rng.poisson(0.4, n)
    base_fare = np.select([pclass == 1, pclass == 2], [84.0, 21.0], default=13.0)
    fare = np.round(base_fare * rng.lognormal(0.0, 0.45, n), 2)
    embarked = rng.choice(["S", "C", "Q"], size=n, p=[0.72, 0.19, 0.09])

    # Survival probability: women and higher classes survive more, children get a
    # boost, very large families and old age reduce the odds.
    logit = (
        -0.9
        + 3.0 * (sex == "female")
        + 1.1 * (pclass == 1)
        + 0.2 * (pclass == 2)
        - 0.8 * (pclass == 3)
        + 0.9 * (age < 12)
        - 0.012 * age
        + 0.004 * fare
        - 0.25 * sibsp
    )
    prob = 1.0 / (1.0 + np.exp(-logit))
    survived = rng.binomial(1, prob)

    df = pd.DataFrame(
        {
            "pclass": pclass.astype(int),
            "sex": sex,
            "age": age,
            "sibsp": sibsp.astype(int),
            "parch": parch.astype(int),
            "fare": fare,
            "embarked": embarked,
        }
    )

    # Inject realistic missingness AFTER generating the target (the target does
    # not depend on the missing entries, only on the underlying values).
    age_missing = rng.random(n) < 0.20
    df.loc[age_missing, "age"] = np.nan
    emb_missing = rng.random(n) < 0.01
    df.loc[emb_missing, "embarked"] = None

    y = pd.Series(survived, name="survived")
    return df, y


# ---------------------------------------------------------------------------
# Time-series generators
# ---------------------------------------------------------------------------


def make_time_series_trend_seasonality(
    n: int = 365,
    slope: float = 0.03,
    period: int = 30,
    seasonal_amp: float = 3.0,
    noise: float = 1.0,
    seed: int = 0,
):
    """Linear trend + sinusoidal seasonality + noise. Returns (t[n], y[n]).

    ``t`` is integer time 0..n-1; ``y`` = slope*t + seasonal_amp*sin(2 pi t /
    period) + Gaussian noise. The textbook example of a non-stationary series.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    trend = slope * t
    seasonal = seasonal_amp * np.sin(2 * np.pi * t / period)
    y = trend + seasonal + noise * rng.standard_normal(n)
    return t, y


def make_noisy_sine_series(n: int = 300, periods: float = 5.0, noise: float = 0.2, seed: int = 0):
    """Noisy sine wave. Returns (t[n], y[n]) with t spanning ``periods`` cycles."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, periods * 2 * np.pi, n)
    y = np.sin(t) + noise * rng.standard_normal(n)
    return t, y


def make_ar_process(n: int = 300, coeffs=(0.6, -0.3), noise: float = 0.5, seed: int = 0):
    """Autoregressive AR(p) series y_t = sum_i coeffs[i]*y_{t-1-i} + eps. Returns y[n]."""
    rng = np.random.default_rng(seed)
    coeffs = np.asarray(coeffs, dtype=float)
    p = len(coeffs)
    y = np.zeros(n)
    y[:p] = rng.standard_normal(p)
    for t in range(p, n):
        y[t] = coeffs @ y[t - p : t][::-1] + noise * rng.standard_normal()
    return y


def make_regime_switching_series(
    n: int = 400, switch_prob: float = 0.01, noise: float = 0.6, seed: int = 0
):
    """Series that flips between two regimes (different mean + slope).

    A hidden state switches with probability ``switch_prob`` each step; regime 0
    drifts down around a low mean, regime 1 drifts up around a high mean. Returns
    ``(y[n], regime[n])`` so notebooks can show how a model trained on one regime
    degrades when the regime shifts.
    """
    rng = np.random.default_rng(seed)
    params = {0: (-2.0, -0.01), 1: (3.0, 0.02)}  # (mean, slope)
    regime = np.zeros(n, dtype=int)
    state = 0
    for t in range(n):
        if rng.random() < switch_prob:
            state = 1 - state
        regime[t] = state
    mean = np.array([params[r][0] for r in regime])
    slope = np.array([params[r][1] for r in regime])
    y = mean + slope * np.arange(n) + noise * rng.standard_normal(n)
    return y, regime


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


def make_anomaly_dataset(
    n_normal: int = 300, n_anomalies: int = 15, n_features: int = 2, seed: int = 0
):
    """Dense normal cluster plus scattered anomalies. Returns (X, y) with y in {0,1}.

    Normals are a tight Gaussian blob at the origin; anomalies are drawn from a
    much wider uniform box. ``y == 1`` marks the anomalies. Rows are shuffled.
    """
    rng = np.random.default_rng(seed)
    normal = rng.standard_normal((n_normal, n_features))
    anomalies = rng.uniform(-6.0, 6.0, size=(n_anomalies, n_features))
    X = np.vstack([normal, anomalies])
    y = np.concatenate([np.zeros(n_normal, dtype=int), np.ones(n_anomalies, dtype=int)])
    perm = rng.permutation(len(X))
    return X[perm], y[perm]


# ---------------------------------------------------------------------------
# Splitting helper
# ---------------------------------------------------------------------------


def train_validation_test_split(
    X, y, val_size: float = 0.2, test_size: float = 0.2, stratify: bool = False, seed: int = 0
):
    """Split into train / validation / test. Returns 6 objects.

    ``(X_train, X_val, X_test, y_train, y_val, y_test)``. The test set is carved
    off first, then the remainder is split into train/validation, so the test
    fraction is exact and the validation fraction is relative to the whole.
    Set ``stratify=True`` for classification to preserve class ratios in each
    split.
    """
    strat = y if stratify else None
    X_rest, X_test, y_rest, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=strat
    )
    # val_size is expressed as a fraction of the ORIGINAL data.
    rel_val = val_size / (1.0 - test_size)
    strat_rest = y_rest if stratify else None
    X_train, X_val, y_train, y_val = train_test_split(
        X_rest, y_rest, test_size=rel_val, random_state=seed, stratify=strat_rest
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def make_capstone_dataset(n: int = 40, x_range=(-3.0, 3.0), noise: float = 0.35, seed: int = 0):
    """Shared 1-D regression data for the cross-book capstone (the same problem).

    The SAME generator is defined identically in every analytics book so each can
    solve one identical problem from its own lens without importing the others.
    True curve f(x) = sin(1.5 x) + 0.3 x, with Gaussian noise. Returns (x, y) as
    float64 arrays sorted by x.
    """
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(x_range[0], x_range[1], n))
    f = np.sin(1.5 * x) + 0.3 * x
    y = f + noise * rng.standard_normal(n)
    return x, y
