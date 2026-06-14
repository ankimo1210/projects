"""Tier-0 baselines — the bar every fancier model must clear.

If a Ridge or a gradient-boosted tree cannot beat "predict zero", "predict the
training mean", or "the feature predicts itself" on the same out-of-sample walk,
the complexity is not earning its keep. These are the honest reference points the
platform always reports alongside the candidate model.
"""

from __future__ import annotations

import pandas as pd

from .base import Model


class ZeroModel(Model):
    """Predict 0 for everything (no skill / no position)."""

    name = "zero"

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ZeroModel:
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(0.0, index=X.index, name="prediction")


class MeanModel(Model):
    """Predict the (constant) mean of the training label."""

    name = "mean"

    def __init__(self) -> None:
        self.mu = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> MeanModel:
        self.mu = float(y.mean())
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(self.mu, index=X.index, name="prediction")


class PersistenceModel(Model):
    """Use one feature directly as the prediction (e.g. momentum persists).

    No fitting — this is the "the signal is its own forecast" baseline. The
    chosen ``feature`` must be a column of the design matrix.
    """

    def __init__(self, feature: str) -> None:
        self.feature = feature
        self.name = f"persist[{feature}]"

    def fit(self, X: pd.DataFrame, y: pd.Series) -> PersistenceModel:
        if self.feature not in X.columns:
            raise KeyError(f"feature {self.feature!r} not in design matrix {list(X.columns)}")
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return X[self.feature].rename("prediction")
