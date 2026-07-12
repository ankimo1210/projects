"""Reusable diagnostics for rough paths and volatility proxies."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def acf_fft(x: ArrayLike, max_lag: int) -> FloatArray:
    """Estimate an unbiased autocorrelation function using an FFT."""
    values = np.asarray(x, dtype=np.float64)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("x must be a one-dimensional series with at least two values")
    if not isinstance(max_lag, (int, np.integer)) or not 0 <= max_lag < values.size:
        raise ValueError("max_lag must lie between zero and len(x)-1")
    if not np.all(np.isfinite(values)):
        raise ValueError("x must contain only finite values")

    centered = values - values.mean()
    n = centered.size
    n_fft = 1 << (2 * n - 1).bit_length()
    spectrum = np.fft.rfft(centered, n=n_fft)
    autocovariance = np.fft.irfft(spectrum * spectrum.conjugate(), n=n_fft)[: max_lag + 1].real
    autocovariance /= n - np.arange(max_lag + 1)
    if autocovariance[0] <= 0:
        raise ValueError("autocorrelation is undefined for a constant series")
    return np.asarray(autocovariance / autocovariance[0], dtype=np.float64)


def log_spaced_lags(
    n: int,
    n_lags: int = 15,
    max_frac: float = 0.10,
) -> NDArray[np.int64]:
    """Choose unique log-spaced lags without using the noisy long-lag tail."""
    if not isinstance(n, (int, np.integer)) or n < 4:
        raise ValueError("n must be an integer of at least 4")
    if not isinstance(n_lags, (int, np.integer)) or n_lags < 3:
        raise ValueError("n_lags must be an integer of at least 3")
    if not 0 < max_frac <= 0.5:
        raise ValueError("max_frac must lie in (0, 0.5]")
    maximum = max(2, min(n - 1, int(np.floor(n * max_frac))))
    lags = np.unique(np.rint(np.geomspace(1, maximum, num=n_lags)).astype(np.int64))
    return lags


def structure_function(
    paths: ArrayLike,
    q_values: ArrayLike,
    lags: ArrayLike,
) -> FloatArray:
    """Calculate empirical structure functions over paths and time origins."""
    values = np.asarray(paths, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    if values.ndim != 2 or values.shape[1] < 2:
        raise ValueError("paths must have shape (n_paths, n_times) or (n_times,)")
    if not np.all(np.isfinite(values)):
        raise ValueError("paths must contain only finite values")
    orders = np.asarray(q_values, dtype=np.float64)
    lag_values = np.asarray(lags, dtype=np.int64)
    if orders.ndim != 1 or orders.size == 0 or np.any(orders <= 0):
        raise ValueError("q_values must be a non-empty vector of positive orders")
    if (
        lag_values.ndim != 1
        or lag_values.size == 0
        or np.any(lag_values < 1)
        or np.any(lag_values >= values.shape[1])
    ):
        raise ValueError("lags must be positive and smaller than the path length")

    result = np.empty((orders.size, lag_values.size), dtype=np.float64)
    for column, lag in enumerate(lag_values):
        absolute = np.abs(values[:, lag:] - values[:, :-lag])
        for row, order in enumerate(orders):
            result[row, column] = np.mean(absolute**order)
    return result


def rolling_realized_variance(returns: ArrayLike, window: int) -> FloatArray:
    """Return rolling sums of squared returns, with leading values as NaN."""
    values = np.asarray(returns, dtype=np.float64)
    if values.ndim not in {1, 2} or values.shape[-1] < 1:
        raise ValueError("returns must be one- or two-dimensional")
    if not isinstance(window, (int, np.integer)) or not 1 <= window <= values.shape[-1]:
        raise ValueError("window must lie between one and the series length")
    squared = values**2
    cumulative = np.concatenate(
        (np.zeros((*values.shape[:-1], 1)), np.cumsum(squared, axis=-1)), axis=-1
    )
    rolling = cumulative[..., window:] - cumulative[..., :-window]
    output = np.full(values.shape, np.nan, dtype=np.float64)
    output[..., window - 1 :] = rolling
    return output
