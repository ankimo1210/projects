"""Tier-4 time-series forecasting: classical baselines + a foundation-model adapter.

Foundation models (Chronos, TimesFM, Moirai) forecast a series' future from its
own history — a different paradigm from the cross-sectional regressors of Tiers
0-3. This module defines a small univariate ``Forecaster`` contract, ships real
classical baselines (seasonal-naive, AR) that need no extra deps, and exposes an
import-gated loader for heavy foundation models. The baselines are what a
foundation model must beat — we never fabricate a foundation-model result, and the
loader raises a clear, actionable error when the optional backend is absent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class Forecaster(ABC):
    """Univariate forecaster: fit on a history series, predict the next h steps."""

    name: str = "forecaster"

    @abstractmethod
    def fit(self, y: pd.Series) -> Forecaster: ...

    @abstractmethod
    def predict(self, horizon: int) -> np.ndarray: ...


class SeasonalNaiveForecaster(Forecaster):
    """Repeat the last ``season`` observations (``season=1`` is the random-walk naive)."""

    def __init__(self, season: int = 1) -> None:
        self.season = season
        self.name = f"seasonal_naive[{season}]"
        self._tail: np.ndarray | None = None

    def fit(self, y: pd.Series) -> SeasonalNaiveForecaster:
        v = np.asarray(y.dropna(), dtype="float64")
        if len(v) < self.season:
            raise ValueError("series shorter than the season")
        self._tail = v[-self.season :]
        return self

    def predict(self, horizon: int) -> np.ndarray:
        reps = int(np.ceil(horizon / self.season))
        return np.tile(self._tail, reps)[:horizon]


class ARForecaster(Forecaster):
    """Autoregressive AR(p) fit by least squares, forecast recursively. No deps."""

    def __init__(self, p: int = 5) -> None:
        self.p = p
        self.name = f"ar[{p}]"
        self.coef_: np.ndarray | None = None
        self._buf: list[float] = []

    def fit(self, y: pd.Series) -> ARForecaster:
        v = np.asarray(y.dropna(), dtype="float64")
        p = self.p
        if len(v) <= p + 1:
            raise ValueError("series too short for the chosen order p")
        rows = [[*v[t - p : t][::-1], 1.0] for t in range(p, len(v))]  # [y_{t-1..t-p}, 1]
        target = v[p:]
        self.coef_, *_ = np.linalg.lstsq(np.array(rows), target, rcond=None)
        self._buf = list(v[-p:])
        return self

    def predict(self, horizon: int) -> np.ndarray:
        p = self.p
        buf = list(self._buf)
        out = []
        for _ in range(horizon):
            feats = [*buf[-p:][::-1], 1.0]
            yhat = float(np.dot(self.coef_, feats))
            out.append(yhat)
            buf.append(yhat)
        return np.array(out)


class ChronosForecaster(Forecaster):
    """Adapter wrapping an Amazon Chronos pipeline as a :class:`Forecaster`.

    Foundation models condition on a context series rather than "fitting", so
    ``fit`` just stores the history and ``predict`` asks the pipeline for the
    median sample-path of the next ``horizon`` steps. Built by
    :func:`load_foundation`; not constructed directly (it needs a live pipeline).
    """

    name = "chronos"

    def __init__(self, pipeline, *, quantile: float = 0.5) -> None:
        self._pipeline = pipeline
        self.quantile = quantile
        self._context: np.ndarray | None = None

    def fit(self, y: pd.Series) -> ChronosForecaster:
        self._context = np.asarray(y.dropna(), dtype="float64")
        return self

    def predict(self, horizon: int) -> np.ndarray:
        import torch

        ctx = torch.tensor(self._context)
        forecast = self._pipeline.predict(ctx, prediction_length=horizon)
        samples = forecast[0]  # [num_samples, horizon] for the single series
        samples = samples.numpy() if hasattr(samples, "numpy") else np.asarray(samples)
        return np.quantile(samples, self.quantile, axis=0)


def load_foundation(
    name: str = "chronos",
    *,
    model_name: str = "amazon/chronos-t5-small",
    device: str | None = None,
    **_kw,
) -> Forecaster:
    """Load a time-series foundation model as a :class:`Forecaster` (optional dep).

    Heavy backends (torch + model weights) are NOT a hard dependency of quantkit. This
    raises a clear, actionable :class:`ImportError` if the backend is missing,
    rather than silently degrading — use the classical forecasters above as the
    always-available baseline.
    """
    if name == "chronos":
        try:
            import torch
            from chronos import ChronosPipeline
        except ImportError as e:
            raise ImportError(
                "Chronos foundation model needs optional deps. Install with: "
                "pip install 'chronos-forecasting' torch  (Tier-4 is optional; "
                "the classical forecasters in quantkit.models.foundation are always available)."
            ) from e
        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        pipeline = ChronosPipeline.from_pretrained(model_name, device_map=dev)
        return ChronosForecaster(pipeline)
    raise KeyError(f"unknown foundation model {name!r} (supported: 'chronos')")
