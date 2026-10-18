"""Model ladder L2-L3, hyperparameter grids and seed-averaged fitting (design §6.2-6.3).

Non-OLS models learn standardized targets and return forecasts in target units. The OLS
models (P2, P3 and the CP regression) fit raw targets.
"""

from __future__ import annotations

import itertools
import warnings
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNet, LinearRegression
from sklearn.neural_network import MLPRegressor

Params = tuple[tuple[str, object], ...]


def grid(**axes: tuple) -> tuple[Params, ...]:
    names = sorted(axes)
    return tuple(
        tuple(zip(names, values, strict=True))
        for values in itertools.product(*(axes[name] for name in names))
    )


@dataclass(frozen=True)
class ModelSpec:
    name: str
    inputs: str  # key of features.INPUTS
    kind: str  # "ols", "en", "et", "hgb" or "mlp"
    grid: tuple[Params, ...] = ((),)
    n_seeds: int = 1


EN_L1_RATIOS = (0.1, 0.5, 0.9)
EN_POINTS = 20
ET_GRID = grid(max_depth=(2, 4, 6), min_samples_leaf=(5, 20), max_features=(0.3, 1.0))
HGB_GRID = grid(
    learning_rate=(0.03, 0.1), max_depth=(2, 3), max_iter=(100, 300), l2_regularization=(0.0, 1.0)
)
NN_ALPHAS = (1e-4, 1e-3, 1e-2)
NN_SEEDS = 20


def ladder(nn_seeds: int = NN_SEEDS) -> dict[str, ModelSpec]:
    return {
        "ols_p": ModelSpec("ols_p", "P", "ols"),
        "ols_pm": ModelSpec("ols_pm", "PM", "ols"),
        "cp": ModelSpec("cp", "F", "ols"),
        "en": ModelSpec("en", "FM", "en"),
        "et": ModelSpec("et", "FM", "et", ET_GRID),
        "hgb": ModelSpec("hgb", "FM", "hgb", HGB_GRID),
        "nn_f": ModelSpec(
            "nn_f", "F", "mlp", grid(hidden_layer_sizes=((3,),), alpha=NN_ALPHAS), nn_seeds
        ),
        "nn_fm": ModelSpec(
            "nn_fm", "FM", "mlp", grid(hidden_layer_sizes=((32, 16),), alpha=NN_ALPHAS), nn_seeds
        ),
    }


def en_grid(X: np.ndarray, z: np.ndarray) -> tuple[Params, ...]:
    """Twenty log-spaced alphas from alpha_max down to alpha_max / 1000 for each l1_ratio."""
    reach = float(np.abs(X.T @ np.asarray(z).reshape(len(X), -1)).max()) / len(X)
    out: list[Params] = []
    for l1_ratio in EN_L1_RATIOS:
        top = max(reach / l1_ratio, 1e-12)
        out.extend(
            (("alpha", float(alpha)), ("l1_ratio", l1_ratio))
            for alpha in top * np.logspace(0.0, -3.0, EN_POINTS)
        )
    return tuple(out)


def estimator(kind: str, params: Params, seed: int):
    kw = dict(params)
    if kind == "ols":
        return LinearRegression()
    if kind == "en":
        return ElasticNet(max_iter=20_000, **kw)
    if kind == "et":
        return ExtraTreesRegressor(n_estimators=500, n_jobs=1, random_state=seed, **kw)
    if kind == "hgb":
        return HistGradientBoostingRegressor(early_stopping=False, random_state=seed, **kw)
    if kind == "mlp":
        return MLPRegressor(solver="adam", max_iter=500, random_state=seed, **kw)
    raise ValueError(f"unknown model kind {kind!r}")


def fit_predict(
    kind: str, params: Params, n_seeds: int, X: np.ndarray, y: np.ndarray, X_new: np.ndarray
) -> np.ndarray:
    y = np.asarray(y, dtype=float).reshape(len(X), -1)
    if kind == "ols":
        return LinearRegression().fit(X, y).predict(X_new).reshape(len(X_new), -1)
    mean = y.mean(axis=0)
    std = y.std(axis=0)
    std = np.where(std > 0, std, 1.0)
    z = (y - mean) / std
    target = z[:, 0] if z.shape[1] == 1 else z
    total = np.zeros((len(X_new), y.shape[1]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        for seed in range(n_seeds):
            model = estimator(kind, params, seed).fit(X, target)
            total += model.predict(X_new).reshape(len(X_new), -1)
    return total / n_seeds * std + mean
