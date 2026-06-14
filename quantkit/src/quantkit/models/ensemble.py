"""Model combination — averaging ensembles and out-of-fold stacking.

Combining models usually beats picking one. :class:`EnsembleModel` blends member
predictions with fixed weights. :class:`StackingModel` learns the blend: it builds
**out-of-fold** base predictions on the training window (each training row is
predicted by base models that never saw it) and fits a meta-model on those, which
avoids the leakage of stacking on in-sample base fits. Both honor the standard
fit/predict contract, so the same walk-forward harness and baseline comparison
apply — a stack is only worth it if it beats its own members out of sample.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd

from .base import Model


class EnsembleModel(Model):
    """Weighted average of member models' predictions (equal weights by default)."""

    def __init__(
        self,
        models: Sequence[Model],
        weights: Sequence[float] | None = None,
        name: str = "ensemble",
    ):
        self.models = list(models)
        if not self.models:
            raise ValueError("need at least one member model")
        self.weights = weights
        self.name = name

    def _norm_weights(self) -> np.ndarray:
        if self.weights is None:
            w = np.ones(len(self.models))
        else:
            w = np.asarray(self.weights, dtype=float)
            if len(w) != len(self.models):
                raise ValueError("weights length must match number of models")
        return w / w.sum()

    def fit(self, X: pd.DataFrame, y: pd.Series) -> EnsembleModel:
        for m in self.models:
            m.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        w = self._norm_weights()
        blended = sum(wi * m.predict(X) for wi, m in zip(w, self.models, strict=True))
        return blended.rename("prediction")


class StackingModel(Model):
    """Stacked generalization with time-ordered out-of-fold meta-features.

    ``base_models`` and ``meta_model`` are **factories** (zero-arg callables returning
    a fresh :class:`Model`), matching the rest of :mod:`quantkit.models`. The training
    dates are split into ``n_splits`` contiguous blocks; each block's rows are
    predicted by base models fit on the other blocks, giving leakage-free meta-features
    on which the meta-model is trained. For test prediction the base models are refit
    on the full training set.
    """

    def __init__(
        self,
        base_models: Sequence[Callable[[], Model]],
        meta_model: Callable[[], Model],
        *,
        n_splits: int = 5,
        name: str = "stacking",
    ):
        self.base_factories = list(base_models)
        self.meta_factory = meta_model
        self.n_splits = n_splits
        self.name = name
        self._cols = [f"m{i}" for i in range(len(self.base_factories))]
        self._base_full: list[Model] = []
        self._meta: Model | None = None

    def _meta_features(self, X: pd.DataFrame, models: Sequence[Model]) -> pd.DataFrame:
        return pd.DataFrame(
            {c: m.predict(X) for c, m in zip(self._cols, models, strict=True)}, index=X.index
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> StackingModel:
        dates = X.index.get_level_values("date")
        unique = pd.DatetimeIndex(sorted(dates.unique()))
        blocks = np.array_split(np.arange(len(unique)), min(self.n_splits, len(unique)))
        oof = pd.DataFrame(index=X.index, columns=self._cols, dtype="float64")
        for blk in blocks:
            held_dates = unique[blk]
            held = dates.isin(held_dates)
            if held.all() or not held.any():
                continue
            Xtr, ytr = X[~held], y[~held]
            for c, fac in zip(self._cols, self.base_factories, strict=True):
                m = fac().fit(Xtr, ytr)
                oof.loc[held, c] = m.predict(X[held]).to_numpy()
        meta_train = oof.dropna()
        self._meta = self.meta_factory().fit(meta_train, y.loc[meta_train.index])
        self._base_full = [fac().fit(X, y) for fac in self.base_factories]
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        if self._meta is None:
            raise RuntimeError("StackingModel must be fit before predict")
        z = self._meta_features(X, self._base_full)
        return self._meta.predict(z).rename("prediction")
