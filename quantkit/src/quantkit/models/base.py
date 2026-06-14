"""Common model interface.

Every model — a naive baseline or a fitted sklearn estimator — implements the
same tiny contract: ``fit(X, y)`` then ``predict(X) -> Series``. ``X`` is a
``(date, asset)``-indexed feature frame and ``y`` the matching label Series (see
:mod:`quantkit.models.design`). Keeping one interface means the walk-forward harness
and the backtest engine treat a baseline and a gradient-boosted tree identically
— which is the whole point: complex models are only worth it if they beat the
simple ones on the *same* out-of-sample evaluation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class Model(ABC):
    """Fit/predict over a (date, asset)-indexed design matrix."""

    name: str = "model"

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> Model: ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> pd.Series: ...


class SklearnModel(Model):
    """Adapter around any sklearn-style regressor.

    Optional standardization fits its mean/std on the **training** ``X`` only and
    reuses them at predict time, so test statistics never leak into the fit.
    """

    def __init__(self, estimator, name: str | None = None, *, standardize: bool = True):
        self.estimator = estimator
        self.name = name or type(estimator).__name__
        self.standardize = standardize
        self._mu: pd.Series | None = None
        self._sd: pd.Series | None = None

    def _fit_scaler(self, X: pd.DataFrame) -> np.ndarray:
        if not self.standardize:
            return X.to_numpy()
        self._mu = X.mean()
        self._sd = X.std(ddof=0).replace(0.0, 1.0)
        return ((X - self._mu) / self._sd).to_numpy()

    def _apply_scaler(self, X: pd.DataFrame) -> np.ndarray:
        if not self.standardize:
            return X.to_numpy()
        return ((X - self._mu) / self._sd).to_numpy()

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SklearnModel:
        self.estimator.fit(self._fit_scaler(X), y.to_numpy())
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        pred = self.estimator.predict(self._apply_scaler(X))
        return pd.Series(pred, index=X.index, name="prediction")
