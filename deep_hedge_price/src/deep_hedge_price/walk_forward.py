"""Classical and small neural volatility forecasting challengers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn


@dataclass(frozen=True)
class Garch11Fit:
    """Deterministic Gaussian-QMLE grid fit for a GARCH(1,1) baseline."""

    omega: float
    alpha: float
    beta: float
    negative_log_likelihood: float


def persistence_forecast(values: np.ndarray) -> np.ndarray:
    series = np.asarray(values, dtype=float)
    if series.ndim != 1 or len(series) < 2:
        raise ValueError("values must contain at least two observations")
    return np.r_[series[0], series[:-1]]


def ewma_forecast(values: np.ndarray, decay: float = 0.94) -> np.ndarray:
    series = np.asarray(values, dtype=float)
    if series.ndim != 1 or len(series) < 2 or not 0 < decay < 1:
        raise ValueError("invalid values or decay")
    result = np.empty_like(series)
    result[0] = series[0]
    for index in range(1, len(series)):
        result[index] = decay * result[index - 1] + (1 - decay) * series[index - 1]
    return result


def garch11_variance_forecast(
    returns: np.ndarray,
    *,
    omega: float,
    alpha: float,
    beta: float,
    initial_variance: float | None = None,
) -> np.ndarray:
    """One-step GARCH(1,1) variance forecasts using information through ``t-1``."""

    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) < 2 or np.any(~np.isfinite(values)):
        raise ValueError("returns must contain at least two finite observations")
    if (
        not np.isfinite(omega)
        or not np.isfinite(alpha)
        or not np.isfinite(beta)
        or omega <= 0.0
        or alpha < 0.0
        or beta < 0.0
        or alpha + beta >= 1.0
    ):
        raise ValueError("GARCH parameters must be positive and stationary")
    if initial_variance is None:
        initial = float(np.var(values, ddof=0))
    else:
        initial = float(initial_variance)
    if not np.isfinite(initial) or initial <= 0.0:
        raise ValueError("initial_variance must be finite and positive")
    forecast = np.empty_like(values)
    forecast[0] = initial
    for index in range(1, len(values)):
        forecast[index] = omega + alpha * values[index - 1] ** 2 + beta * forecast[index - 1]
    return forecast


def fit_garch11(returns: np.ndarray) -> Garch11Fit:
    """Fit a stable GARCH(1,1) baseline without an optional dependency.

    The compact deterministic grid is intentional for the CPU reference path:
    it produces an auditable baseline and cannot acquire a random optimizer
    state.  Parameters are selected only from the supplied training window.
    """

    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) < 30 or np.any(~np.isfinite(values)):
        raise ValueError("GARCH fitting needs at least 30 finite returns")
    long_run = max(float(np.mean(values**2)), np.finfo(float).tiny)
    best: Garch11Fit | None = None
    for alpha in (0.03, 0.06, 0.10, 0.15):
        for beta in (0.75, 0.82, 0.88, 0.93):
            persistence = alpha + beta
            if persistence >= 0.995:
                continue
            omega = long_run * (1.0 - persistence)
            variance = garch11_variance_forecast(
                values,
                omega=omega,
                alpha=alpha,
                beta=beta,
                initial_variance=long_run,
            )
            likelihood = float(np.mean(np.log(variance) + values**2 / variance))
            candidate = Garch11Fit(omega, alpha, beta, likelihood)
            if best is None or candidate.negative_log_likelihood < best.negative_log_likelihood:
                best = candidate
    if best is None:  # pragma: no cover - the fixed grid always has feasible points
        raise RuntimeError("GARCH parameter grid has no stationary candidate")
    return best


def garch11_aggregate_forecast(
    one_step_variance: np.ndarray | float,
    *,
    horizon: int,
    omega: float,
    alpha: float,
    beta: float,
) -> np.ndarray | float:
    """Sum conditional variance forecasts over ``horizon`` future days."""

    first = np.asarray(one_step_variance, dtype=float)
    if (
        horizon < 1
        or np.any(~np.isfinite(first))
        or np.any(first <= 0.0)
        or omega <= 0.0
        or alpha < 0.0
        or beta < 0.0
        or alpha + beta >= 1.0
    ):
        raise ValueError("invalid GARCH aggregate forecast inputs")
    persistence = alpha + beta
    current = first.copy()
    total = current.copy()
    for _ in range(1, horizon):
        current = omega + persistence * current
        total = total + current
    return float(total) if total.ndim == 0 else total


def har_features(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return daily/weekly/monthly lag features and aligned targets."""
    series = np.asarray(values, dtype=float)
    if series.ndim != 1 or len(series) <= 22:
        raise ValueError("HAR needs more than 22 observations")
    rows = []
    targets = []
    for index in range(22, len(series)):
        rows.append(
            [series[index - 1], series[index - 5 : index].mean(), series[index - 22 : index].mean()]
        )
        targets.append(series[index])
    return np.asarray(rows), np.asarray(targets)


@dataclass(frozen=True)
class LinearForecast:
    intercept: float
    coefficients: np.ndarray

    def predict(self, features: np.ndarray) -> np.ndarray:
        return self.intercept + np.asarray(features, dtype=float) @ self.coefficients


def fit_regularized_linear(
    features: np.ndarray, targets: np.ndarray, ridge: float = 1e-4
) -> LinearForecast:
    x = np.asarray(features, dtype=float)
    y = np.asarray(targets, dtype=float)
    if x.ndim != 2 or y.shape != (len(x),) or ridge < 0:
        raise ValueError("invalid feature/target shapes or ridge")
    design = np.column_stack([np.ones(len(x)), x])
    penalty = ridge * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return LinearForecast(intercept=float(beta[0]), coefficients=beta[1:])


class SequenceForecaster(nn.Module):
    """Small TCN/LSTM/encoder-only Transformer with one common interface."""

    def __init__(self, kind: str, *, hidden: int = 12):
        super().__init__()
        if kind not in {"harnet", "tcn", "lstm", "transformer"}:
            raise ValueError("kind must be harnet, tcn, lstm, or transformer")
        self.kind = kind
        self.input_projection = nn.Linear(1, hidden)
        self.last_attention: torch.Tensor | None = None
        if kind == "harnet":
            self.encoder = nn.Sequential(nn.Linear(3, hidden), nn.SiLU(), nn.Linear(hidden, hidden))
        elif kind == "tcn":
            self.encoder = nn.Sequential(
                nn.Conv1d(hidden, hidden, kernel_size=3, padding=2, dilation=1),
                nn.SiLU(),
                nn.Conv1d(hidden, hidden, kernel_size=3, padding=2, dilation=2),
                nn.SiLU(),
            )
        elif kind == "lstm":
            self.encoder = nn.LSTM(hidden, hidden, batch_first=True)
        else:
            self.encoder = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
            self.feed_forward = nn.Sequential(
                nn.Linear(hidden, 2 * hidden), nn.SiLU(), nn.Linear(2 * hidden, hidden)
            )
        self.output = nn.Linear(hidden, 1)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        if sequence.ndim != 2:
            raise ValueError("sequence must have shape [batch, time]")
        if self.kind == "harnet":
            if sequence.shape[1] < 22:
                raise ValueError("HARNet needs at least 22 lags")
            features = torch.stack(
                (
                    sequence[:, -1],
                    sequence[:, -5:].mean(dim=1),
                    sequence[:, -22:].mean(dim=1),
                ),
                dim=1,
            )
            encoded = self.encoder(features)
        else:
            embedded = self.input_projection(sequence.unsqueeze(-1))
        if self.kind == "tcn":
            encoded = self.encoder(embedded.transpose(1, 2))[..., : sequence.shape[1]].mean(dim=-1)
        elif self.kind == "lstm":
            encoded, _ = self.encoder(embedded)
            encoded = encoded[:, -1]
        elif self.kind == "transformer":
            encoded, attention = self.encoder(
                embedded,
                embedded,
                embedded,
                need_weights=True,
                average_attn_weights=False,
            )
            self.last_attention = attention.detach()
            encoded = self.feed_forward(encoded).mean(dim=1)
        return self.output(encoded).squeeze(-1)


def fit_sequence_forecaster(
    model: SequenceForecaster,
    sequences: torch.Tensor,
    targets: torch.Tensor,
    *,
    epochs: int = 20,
    learning_rate: float = 0.01,
) -> list[float]:
    if epochs < 1 or sequences.ndim != 2 or targets.shape != (len(sequences),):
        raise ValueError("invalid training inputs")
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    history = []
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = torch.mean((model(sequences) - targets) ** 2)
        loss.backward()
        optimizer.step()
        history.append(float(loss.detach()))
    return history


def forecast_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    observed = np.asarray(actual, dtype=float)
    forecast = np.asarray(predicted, dtype=float)
    if (
        observed.shape != forecast.shape
        or observed.size == 0
        or np.any(~np.isfinite(observed))
        or np.any(~np.isfinite(forecast))
        or np.any(observed <= 0)
        or np.any(forecast <= 0)
    ):
        raise ValueError("actual/predicted positive variances must match")
    ratio = observed / forecast
    return {
        "rmse": float(np.sqrt(np.mean((forecast - observed) ** 2))),
        "mae": float(np.mean(np.abs(forecast - observed))),
        "qlike": float(np.mean(ratio - np.log(ratio) - 1)),
    }


def block_bootstrap_metric_ci(
    losses: np.ndarray,
    *,
    block_size: int,
    n_bootstrap: int = 500,
    seed: int = 0,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    values = np.asarray(losses, dtype=float)
    if (
        values.ndim != 1
        or np.any(~np.isfinite(values))
        or len(values) < block_size
        or block_size < 1
        or n_bootstrap < 2
        or not 0.0 < confidence < 1.0
    ):
        raise ValueError("invalid bootstrap configuration")
    rng = np.random.default_rng(seed)
    means = []
    n_blocks = int(np.ceil(len(values) / block_size))
    starts = np.arange(0, len(values) - block_size + 1)
    for _ in range(n_bootstrap):
        sample = np.concatenate(
            [values[start : start + block_size] for start in rng.choice(starts, n_blocks)]
        )[: len(values)]
        means.append(sample.mean())
    tail = (1 - confidence) / 2
    return (
        float(values.mean()),
        float(np.quantile(means, tail)),
        float(np.quantile(means, 1 - tail)),
    )
