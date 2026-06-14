"""Tier-3 neural network (cross-sectional MLP).

A feed-forward net via scikit-learn's ``MLPRegressor`` — a real non-linear model
on the same ``(date, asset)`` design matrix and fit/predict contract as Tier 0-2,
so it drops straight into ``walk_forward_predict`` and is compared against the
same baselines. No torch dependency. (Sequence models — LSTM/TCN — and time-series
foundation models are Tier 4, in :mod:`irp.models.foundation`.)
"""

from __future__ import annotations

from sklearn.neural_network import MLPRegressor

from .base import SklearnModel


def mlp(
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    *,
    alpha: float = 1e-3,
    max_iter: int = 500,
    random_state: int = 0,
    **kw,
) -> SklearnModel:
    """A standardized MLP regressor (Tier 3). Inputs are scaled (fit on train only)."""
    est = MLPRegressor(
        hidden_layer_sizes=hidden_layer_sizes,
        alpha=alpha,
        max_iter=max_iter,
        random_state=random_state,
        **kw,
    )
    return SklearnModel(est, name="mlp", standardize=True)
