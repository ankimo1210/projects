"""Forecast accuracy metrics.

Every metric here takes ``actual`` and ``pred`` of shape ``(H,)`` and, where a
scale is needed, the *in-sample* context so the denominator can never see the
evaluation window.  That separation is the whole point: a metric that scales by
the test window silently leaks the answer into the score.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "crps_from_quantiles",
    "mae",
    "mase",
    "pinball",
    "rmsse",
    "scaled_crps",
    "seasonal_scale_mae",
    "seasonal_scale_mse",
    "smape",
]

_EPS = 1e-12


def seasonal_scale_mae(context: np.ndarray, season: int) -> float:
    """In-sample MAE of the seasonal-naive forecast — the MASE denominator.

    Falls back to season 1 when the context is too short to hold a full season,
    and to ``nan`` when even that is degenerate (a constant context).
    """
    x = np.asarray(context, dtype=np.float64)
    m = season if len(x) > season else 1
    if len(x) <= m:
        return float("nan")
    d = np.abs(x[m:] - x[:-m])
    s = float(d.mean())
    return s if s > _EPS else float("nan")


def seasonal_scale_mse(context: np.ndarray, season: int) -> float:
    """In-sample MSE of the seasonal-naive forecast — the RMSSE denominator."""
    x = np.asarray(context, dtype=np.float64)
    m = season if len(x) > season else 1
    if len(x) <= m:
        return float("nan")
    s = float(((x[m:] - x[:-m]) ** 2).mean())
    return s if s > _EPS else float("nan")


def mae(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.abs(np.asarray(actual, float) - np.asarray(pred, float)).mean())


def mase(actual: np.ndarray, pred: np.ndarray, scale: float) -> float:
    """Mean Absolute Scaled Error (Hyndman & Koehler 2006).

    ``scale`` must come from :func:`seasonal_scale_mae` on the context.
    MASE < 1 means the model beat an in-sample seasonal-naive step.
    """
    if not np.isfinite(scale):
        return float("nan")
    return mae(actual, pred) / scale


def rmsse(actual: np.ndarray, pred: np.ndarray, scale_mse: float) -> float:
    """Root Mean Squared Scaled Error (the M5 metric)."""
    if not np.isfinite(scale_mse):
        return float("nan")
    a = np.asarray(actual, float)
    p = np.asarray(pred, float)
    return float(np.sqrt(((a - p) ** 2).mean() / scale_mse))


def smape(actual: np.ndarray, pred: np.ndarray) -> float:
    """Symmetric MAPE in percent, on the 0-200 convention.

    Points where both actual and prediction are zero contribute 0 rather than
    ``nan`` — the forecast was exactly right there.
    """
    a = np.asarray(actual, float)
    p = np.asarray(pred, float)
    denom = np.abs(a) + np.abs(p)
    out = np.zeros_like(denom)
    nz = denom > _EPS
    out[nz] = 200.0 * np.abs(a[nz] - p[nz]) / denom[nz]
    return float(out.mean())


def pinball(actual: np.ndarray, q_pred: np.ndarray, q: float) -> float:
    """Pinball (quantile) loss at level ``q``, averaged over the horizon."""
    a = np.asarray(actual, float)
    p = np.asarray(q_pred, float)
    d = a - p
    return float(np.maximum(q * d, (q - 1.0) * d).mean())


def crps_from_quantiles(
    actual: np.ndarray, quantiles: np.ndarray, levels: np.ndarray
) -> float:
    """CRPS approximated by the quantile-loss integral over a discrete grid.

    ``quantiles`` has shape ``(H, Q)`` and ``levels`` shape ``(Q,)``.  For an
    evenly spaced grid this is the standard ``2 * mean(pinball)`` estimator; it
    understates true CRPS in the tails outside the grid, which is why the
    report compares models on the *same* grid rather than to an absolute value.
    """
    a = np.asarray(actual, float)
    qp = np.asarray(quantiles, float)
    lv = np.asarray(levels, float)
    if qp.shape[0] != a.shape[0] or qp.shape[1] != lv.shape[0]:
        raise ValueError(f"shape mismatch: actual {a.shape}, quantiles {qp.shape}, levels {lv.shape}")
    d = a[:, None] - qp
    loss = np.maximum(lv[None, :] * d, (lv[None, :] - 1.0) * d)
    return float(2.0 * loss.mean())


def scaled_crps(
    actual: np.ndarray, quantiles: np.ndarray, levels: np.ndarray, scale: float
) -> float:
    """CRPS divided by the MASE scale, so it is comparable across series."""
    if not np.isfinite(scale):
        return float("nan")
    return crps_from_quantiles(actual, quantiles, levels) / scale
