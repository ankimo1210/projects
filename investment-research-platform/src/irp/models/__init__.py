"""irp.models — a common fit/predict interface with tiered models.

Tier 0 baselines (:mod:`~irp.models.baselines`: zero / mean / persistence) set the
bar; Tier 1 linear (:mod:`~irp.models.linear`: ridge / lasso / elastic_net), Tier 2
trees (:mod:`~irp.models.tree`: random_forest / gradient_boosting) and Tier 3 neural
(:mod:`~irp.models.neural`: mlp) must beat them on the *same* out-of-sample walk.
Tier 4 univariate forecasting (:mod:`~irp.models.foundation`: seasonal-naive / AR
baselines + an import-gated foundation-model loader) is a different, time-series
paradigm. :func:`~irp.models.design.make_design` builds the ``(date, asset)`` design
matrix; :func:`~irp.models.walkforward.walk_forward_predict` fits per fold and
returns OOS predictions for the backtest engine.
"""

from __future__ import annotations

from .base import Model, SklearnModel
from .baselines import MeanModel, PersistenceModel, ZeroModel
from .design import make_design, predictions_to_panel
from .foundation import ARForecaster, Forecaster, SeasonalNaiveForecaster, load_foundation
from .linear import elastic_net, lasso, ridge
from .neural import mlp
from .tree import gradient_boosting, random_forest
from .walkforward import walk_forward_predict

__all__ = [
    "ARForecaster",
    "Forecaster",
    "MeanModel",
    "Model",
    "PersistenceModel",
    "SeasonalNaiveForecaster",
    "SklearnModel",
    "ZeroModel",
    "elastic_net",
    "gradient_boosting",
    "lasso",
    "load_foundation",
    "make_design",
    "mlp",
    "predictions_to_panel",
    "random_forest",
    "ridge",
    "walk_forward_predict",
]
