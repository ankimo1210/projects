"""Tier-1 linear models (regularized regression).

Thin factories returning :class:`~irp.models.base.SklearnModel` wrappers so they
share the platform's fit/predict contract and train-only standardization.
"""

from __future__ import annotations

from sklearn.linear_model import ElasticNet, Lasso, Ridge

from .base import SklearnModel


def ridge(alpha: float = 1.0, **kw) -> SklearnModel:
    return SklearnModel(Ridge(alpha=alpha, **kw), name="ridge")


def lasso(alpha: float = 1e-3, **kw) -> SklearnModel:
    return SklearnModel(Lasso(alpha=alpha, **kw), name="lasso")


def elastic_net(alpha: float = 1e-3, l1_ratio: float = 0.5, **kw) -> SklearnModel:
    return SklearnModel(ElasticNet(alpha=alpha, l1_ratio=l1_ratio, **kw), name="elastic_net")
