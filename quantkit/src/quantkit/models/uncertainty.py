"""Uncertainty quantification — quantile regression and split-conformal intervals.

A point forecast hides how sure the model is. Two complementary tools:
  * :class:`QuantileModel` fits one gradient-boosted quantile regressor per quantile
    (pinball loss), giving a full predictive spread — but with no coverage guarantee.
  * :class:`ConformalModel` wraps any base model and, using a held-out calibration
    block, produces intervals with a finite-sample **marginal coverage** guarantee of
    ``1-alpha`` under exchangeability (split conformal).

Both return interval-shaped output (a DataFrame), so they live outside the point
fit/predict contract and are used directly rather than via ``walk_forward_predict``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from .base import Model, SklearnModel


class QuantileModel:
    """Gradient-boosted quantile regression: one model per quantile."""

    def __init__(
        self,
        quantiles=(0.1, 0.5, 0.9),
        *,
        n_estimators: int = 200,
        max_depth: int = 3,
        learning_rate: float = 0.05,
        random_state: int = 0,
        **kw,
    ):
        self.quantiles = tuple(quantiles)
        self._cfg = dict(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
            **kw,
        )
        self.name = "quantile_gbm"
        self._models: dict[float, SklearnModel] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series) -> QuantileModel:
        for q in self.quantiles:
            est = GradientBoostingRegressor(loss="quantile", alpha=q, **self._cfg)
            self._models[q] = SklearnModel(est, standardize=False).fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """Predicted quantiles as a frame (columns = the requested quantiles)."""
        return pd.DataFrame({q: self._models[q].predict(X) for q in self.quantiles}, index=X.index)


def quantile_gbm(quantiles=(0.1, 0.5, 0.9), **kw) -> QuantileModel:
    """Factory for a :class:`QuantileModel`."""
    return QuantileModel(quantiles, **kw)


class ConformalModel:
    """Split-conformal prediction intervals around any base point model.

    At fit the (time-ordered) data is split: the earlier ``1 - calib_fraction`` of
    dates train the base model, the later ``calib_fraction`` calibrate the interval
    half-width as the ``1-alpha`` quantile of absolute residuals (with the finite-sample
    ``ceil((n+1)(1-alpha))/n`` correction). ``predict`` returns lower/point/upper.
    """

    def __init__(
        self,
        base: Model,
        *,
        alpha: float = 0.1,
        calib_fraction: float = 0.3,
        name: str = "conformal",
    ):
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0, 1)")
        self.base = base
        self.alpha = alpha
        self.calib_fraction = calib_fraction
        self.name = name
        self.half_width_: float | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ConformalModel:
        dates = X.index.get_level_values("date")
        unique = pd.DatetimeIndex(sorted(dates.unique()))
        n_calib = max(1, round(len(unique) * self.calib_fraction))
        calib_dates = unique[-n_calib:]
        is_calib = dates.isin(calib_dates)
        self.base.fit(X[~is_calib], y[~is_calib])
        resid = (y[is_calib] - self.base.predict(X[is_calib])).abs().to_numpy()
        n = len(resid)
        level = min(1.0, np.ceil((n + 1) * (1 - self.alpha)) / n)  # finite-sample correction
        self.half_width_ = float(np.quantile(resid, level, method="higher"))
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        if self.half_width_ is None:
            raise RuntimeError("ConformalModel must be fit before predict")
        point = self.base.predict(X)
        h = self.half_width_
        return pd.DataFrame({"lower": point - h, "point": point, "upper": point + h}, index=X.index)

    def coverage(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Empirical fraction of ``y`` falling inside the predicted intervals."""
        out = self.predict(X)
        return float(((y >= out["lower"]) & (y <= out["upper"])).mean())
