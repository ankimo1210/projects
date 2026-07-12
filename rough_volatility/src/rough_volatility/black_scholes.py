"""Vectorized Black--Scholes prices and robust call implied volatility."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import brentq
from scipy.special import ndtr

FloatArray = NDArray[np.float64]
type ScalarOrArray = float | FloatArray


def _return_scalar_if_scalar(value: FloatArray) -> ScalarOrArray:
    return float(value) if value.ndim == 0 else value


def _broadcast_inputs(
    s: ArrayLike,
    k: ArrayLike,
    t: ArrayLike,
    sigma: ArrayLike,
    r: ArrayLike,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, FloatArray]:
    arrays = tuple(np.asarray(value, dtype=np.float64) for value in (s, k, t, sigma, r))
    spot, strike, maturity, volatility, rate = np.broadcast_arrays(*arrays)
    if np.any(~np.isfinite(spot)) or np.any(spot <= 0):
        raise ValueError("spot must be finite and positive")
    if np.any(~np.isfinite(strike)) or np.any(strike <= 0):
        raise ValueError("strike must be finite and positive")
    if np.any(~np.isfinite(maturity)) or np.any(maturity < 0):
        raise ValueError("maturity must be finite and non-negative")
    if np.any(~np.isfinite(volatility)) or np.any(volatility < 0):
        raise ValueError("volatility must be finite and non-negative")
    if np.any(~np.isfinite(rate)):
        raise ValueError("rate must be finite")
    return spot, strike, maturity, volatility, rate


def call_price(
    s: ArrayLike,
    k: ArrayLike,
    t: ArrayLike,
    sigma: ArrayLike,
    r: ArrayLike = 0.0,
) -> ScalarOrArray:
    """Return Black--Scholes European call values."""
    spot, strike, maturity, volatility, rate = _broadcast_inputs(s, k, t, sigma, r)
    discount = np.exp(-rate * maturity)
    output = np.maximum(spot - strike * discount, 0.0)
    regular = (maturity > 0) & (volatility > 0)
    if np.any(regular):
        safe_maturity = np.where(regular, maturity, 1.0)
        safe_volatility = np.where(regular, volatility, 1.0)
        sqrt_t = np.sqrt(safe_maturity)
        sigma_sqrt_t = safe_volatility * sqrt_t
        d1 = (
            np.log(spot / strike) + (rate + 0.5 * safe_volatility**2) * safe_maturity
        ) / sigma_sqrt_t
        d2 = d1 - sigma_sqrt_t
        regular_output = spot * ndtr(d1) - strike * discount * ndtr(d2)
        output = np.where(regular, regular_output, output)
    return _return_scalar_if_scalar(np.asarray(output))


def put_price(
    s: ArrayLike,
    k: ArrayLike,
    t: ArrayLike,
    sigma: ArrayLike,
    r: ArrayLike = 0.0,
) -> ScalarOrArray:
    """Return Black--Scholes European put values."""
    spot, strike, maturity, volatility, rate = _broadcast_inputs(s, k, t, sigma, r)
    discount = np.exp(-rate * maturity)
    calls = np.asarray(call_price(spot, strike, maturity, volatility, rate))
    result = calls - spot + strike * discount
    return _return_scalar_if_scalar(np.asarray(result))


def vega(
    s: ArrayLike,
    k: ArrayLike,
    t: ArrayLike,
    sigma: ArrayLike,
    r: ArrayLike = 0.0,
) -> ScalarOrArray:
    """Return Black--Scholes derivative with respect to volatility."""
    spot, strike, maturity, volatility, rate = _broadcast_inputs(s, k, t, sigma, r)
    output = np.zeros_like(spot)
    regular = (maturity > 0) & (volatility > 0)
    if np.any(regular):
        safe_maturity = np.where(regular, maturity, 1.0)
        safe_volatility = np.where(regular, volatility, 1.0)
        sqrt_t = np.sqrt(safe_maturity)
        d1 = (np.log(spot / strike) + (rate + 0.5 * safe_volatility**2) * safe_maturity) / (
            safe_volatility * sqrt_t
        )
        regular_output = spot * np.exp(-0.5 * d1**2) / np.sqrt(2.0 * np.pi) * sqrt_t
        output = np.where(regular, regular_output, output)
    return _return_scalar_if_scalar(np.asarray(output))


def implied_vol(
    price: float,
    s: float,
    k: float,
    t: float,
    r: float = 0.0,
) -> float:
    """Invert a call value, returning NaN rather than raising on failure."""
    values = (price, s, k, t, r)
    if not all(np.isfinite(value) for value in values) or s <= 0 or k <= 0 or t < 0:
        return float("nan")
    lower = max(s - k * np.exp(-r * t), 0.0)
    upper = s
    tolerance = 4.0 * np.finfo(np.float64).eps * max(1.0, s, k)
    if price < lower - tolerance or price >= upper - tolerance:
        return float("nan")
    if abs(price - lower) <= tolerance:
        return 0.0
    if t == 0:
        return float("nan")

    def objective(volatility: float) -> float:
        return float(call_price(s, k, t, volatility, r)) - price

    low, high = 1e-6, 5.0
    try:
        low_value = objective(low)
        high_value = objective(high)
        if low_value > 0 or high_value < 0:
            return float("nan")
        return float(brentq(objective, low, high, xtol=1e-12, rtol=1e-12, maxiter=100))
    except (RuntimeError, ValueError, FloatingPointError):
        return float("nan")
