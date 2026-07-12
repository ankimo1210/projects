"""Synthetic signed-event prices, volatility proxies and noise fragility."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

from rough_volatility.config import NoiseStudyConfig
from rough_volatility.estimators import ESTIMATORS, HurstEstimate, hurst_variogram
from rough_volatility.fbm import fbm_paths
from rough_volatility.random import stream

FloatArray = NDArray[np.float64]


def bin_events(
    times: ArrayLike,
    marks: ArrayLike,
    bin_width: float,
    horizon: float,
) -> pd.DataFrame:
    """Aggregate buy (mark 0) and sell (mark 1) events into regular bins."""
    event_times = np.asarray(times, dtype=np.float64)
    event_marks = np.asarray(marks, dtype=np.int64)
    if bin_width <= 0 or horizon <= 0:
        raise ValueError("bin_width and horizon must be positive")
    if (
        event_times.ndim != 1
        or event_marks.shape != event_times.shape
        or np.any(~np.isfinite(event_times))
        or np.any(event_times < 0)
        or np.any(event_times > horizon)
        or np.any((event_marks < 0) | (event_marks > 1))
    ):
        raise ValueError("event times/marks are invalid")
    n_bins = int(np.ceil(horizon / bin_width))
    bin_indices = np.minimum((event_times / bin_width).astype(int), n_bins - 1)
    buy = np.bincount(bin_indices[event_marks == 0], minlength=n_bins)
    sell = np.bincount(bin_indices[event_marks == 1], minlength=n_bins)
    starts = np.arange(n_bins, dtype=np.float64) * bin_width
    ends = np.minimum(starts + bin_width, horizon)
    return pd.DataFrame(
        {
            "time": ends,
            "bin_start": starts,
            "bin_end": ends,
            "buy_count": buy,
            "sell_count": sell,
            "event_count": buy + sell,
            "imbalance": buy - sell,
        }
    )


def price_from_events(
    bins: pd.DataFrame,
    p0: float,
    tick_eps: float,
    noise_std: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Construct a signed-count price with optional observation noise."""
    if "imbalance" not in bins:
        raise ValueError("bins must contain imbalance")
    if p0 <= 0 or tick_eps <= 0 or noise_std < 0:
        raise ValueError("p0/tick_eps must be positive and noise_std non-negative")
    result = bins.copy()
    latent = p0 + tick_eps * result["imbalance"].to_numpy(dtype=float).cumsum()
    noise = noise_std * rng.standard_normal(len(result)) if noise_std > 0 else 0.0
    price = latent + noise
    returns = np.diff(np.r_[p0, price])
    result["latent_price"] = latent
    result["price"] = price
    result["return"] = returns
    result["abs_return"] = np.abs(returns)
    result["squared_return"] = returns**2
    return result


def rv_diagnostics(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    """Add rolling realized variance and event-intensity proxies."""
    if not {"price", "event_count"} <= set(frame.columns):
        raise ValueError("frame must contain price and event_count")
    if not isinstance(window, (int, np.integer)) or window < 2 or window > len(frame):
        raise ValueError("window must be between 2 and the number of bins")
    result = frame.copy()
    if "return" not in result:
        result["return"] = result["price"].diff().fillna(0.0)
    result["abs_return"] = result["return"].abs()
    result["squared_return"] = result["return"] ** 2
    result["rolling_rv"] = result["squared_return"].rolling(window).sum()
    result["rolling_intensity"] = result["event_count"].rolling(window).mean()
    return result


def effective_hurst_of_log_rv(
    rv: ArrayLike,
    floor_quantile: float = 0.05,
) -> HurstEstimate:
    """Estimate a descriptive H on ``log(RV+floor)`` (not a structural H)."""
    values = np.asarray(rv, dtype=np.float64)
    values = values[np.isfinite(values) & (values >= 0)]
    if values.size < 32:
        raise ValueError("at least 32 finite non-negative RV values are required")
    if not 0 <= floor_quantile < 1:
        raise ValueError("floor_quantile must lie in [0, 1)")
    positive = values[values > 0]
    if positive.size == 0:
        raise ValueError("RV series must contain a positive value")
    floor = float(np.quantile(positive, floor_quantile))
    estimate = hurst_variogram(np.log(values + floor))
    return replace(estimate, estimator="effective_log_rv_variogram")


def pre_average(y: ArrayLike, window: int) -> FloatArray:
    """Return overlapping local means used as a simple noise-robust transform."""
    values = np.asarray(y, dtype=np.float64)
    if values.ndim != 1 or np.any(~np.isfinite(values)):
        raise ValueError("y must be a finite one-dimensional series")
    if not isinstance(window, (int, np.integer)) or not 2 <= window <= values.size:
        raise ValueError("window must lie between 2 and len(y)")
    kernel = np.full(window, 1.0 / window)
    return np.asarray(np.convolve(values, kernel, mode="valid"))


def _aggregate_levels(values: FloatArray, window: int) -> FloatArray:
    n_blocks = values.size // window
    if n_blocks < 1:
        return np.empty(0, dtype=np.float64)
    return values[: n_blocks * window].reshape(n_blocks, window).mean(axis=1)


def noise_fragility_study(config: NoiseStudyConfig, seed: int) -> pd.DataFrame:
    """Run the shared-latent-path estimator sensitivity experiment."""
    config.validate()
    latent = fbm_paths(
        config.latent_h,
        config.n_steps,
        config.n_replications,
        config.horizon,
        stream(seed, "noise_g"),
    ).paths
    noise = stream(seed, "microstructure_noise").standard_normal(latent.shape)
    rows: list[dict[str, float | int | str]] = []
    for noise_std in config.noise_stds:
        observed = latent + noise_std * noise
        for stride in config.strides:
            sampled = observed[:, ::stride]
            for estimator_name in config.estimators:
                estimator = ESTIMATORS[estimator_name]
                for mode in ("raw", "aggregated", "preaveraged"):
                    estimates: list[float] = []
                    for path in sampled:
                        if mode == "raw":
                            transformed = path
                        elif mode == "aggregated":
                            transformed = _aggregate_levels(path, config.aggregate_window)
                        else:
                            transformed = pre_average(path, config.preaverage_window)
                        argument = (
                            np.diff(transformed)
                            if estimator_name == "aggregated_variance"
                            else transformed
                        )
                        try:
                            value = float(estimator(argument).h_hat)
                        except ValueError:
                            continue
                        if np.isfinite(value):
                            estimates.append(value)
                    array = np.asarray(estimates, dtype=np.float64)
                    rows.append(
                        {
                            "noise_std": float(noise_std),
                            "stride": int(stride),
                            "estimator": estimator_name,
                            "mode": mode,
                            "h_hat_mean": float(array.mean()) if array.size else float("nan"),
                            "h_hat_sd": float(array.std(ddof=1))
                            if array.size > 1
                            else float("nan"),
                            "n_rep": int(array.size),
                        }
                    )
    return pd.DataFrame(
        rows,
        columns=[
            "noise_std",
            "stride",
            "estimator",
            "mode",
            "h_hat_mean",
            "h_hat_sd",
            "n_rep",
        ],
    )
