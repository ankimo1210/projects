"""Tier-2 tree ensembles.

Trees are scale-invariant, so standardization is off. Seeds are fixed for
reproducibility (vary the seed explicitly to probe stability).
"""

from __future__ import annotations

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from .base import SklearnModel


def random_forest(
    n_estimators: int = 200, max_depth: int | None = 4, random_state: int = 0, **kw
) -> SklearnModel:
    est = RandomForestRegressor(
        n_estimators=n_estimators, max_depth=max_depth, random_state=random_state, n_jobs=-1, **kw
    )
    return SklearnModel(est, name="random_forest", standardize=False)


def gradient_boosting(
    n_estimators: int = 200,
    max_depth: int = 3,
    learning_rate: float = 0.05,
    random_state: int = 0,
    **kw,
) -> SklearnModel:
    est = GradientBoostingRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        random_state=random_state,
        **kw,
    )
    return SklearnModel(est, name="gradient_boosting", standardize=False)
