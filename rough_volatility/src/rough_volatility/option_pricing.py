"""Monte Carlo call prices, implied-volatility smiles and surfaces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

from rough_volatility.black_scholes import implied_vol, vega

FloatArray = NDArray[np.float64]


def mc_call_prices(
    s_terminal: ArrayLike,
    s0: float,
    log_moneyness: ArrayLike,
    *,
    maturity: float = 1.0,
    r: float = 0.0,
) -> tuple[FloatArray, FloatArray]:
    """Price calls and estimate Monte Carlo standard errors from terminals."""
    terminal = np.asarray(s_terminal, dtype=np.float64)
    moneyness = np.asarray(log_moneyness, dtype=np.float64)
    if terminal.ndim != 1 or terminal.size < 2 or np.any(~np.isfinite(terminal)):
        raise ValueError("s_terminal must be a finite vector with at least two paths")
    if np.any(terminal <= 0):
        raise ValueError("terminal spots must be positive")
    if moneyness.ndim != 1 or moneyness.size == 0 or np.any(~np.isfinite(moneyness)):
        raise ValueError("log_moneyness must be a non-empty finite vector")
    if s0 <= 0 or maturity <= 0 or not np.isfinite(r):
        raise ValueError("s0 and maturity must be positive and r finite")
    forward = s0 * np.exp(r * maturity)
    strikes = forward * np.exp(moneyness)
    discount = np.exp(-r * maturity)
    payoffs = np.maximum(terminal[:, None] - strikes[None, :], 0.0)
    prices = discount * payoffs.mean(axis=0)
    standard_errors = discount * payoffs.std(axis=0, ddof=1) / np.sqrt(terminal.size)
    return np.asarray(prices), np.asarray(standard_errors)


def smile_from_terminals(
    s_terminal: ArrayLike,
    s0: float,
    log_moneyness: ArrayLike,
    *,
    maturity: float,
    r: float = 0.0,
) -> pd.DataFrame:
    """Build a smile table with price and implied-volatility uncertainty."""
    moneyness = np.asarray(log_moneyness, dtype=np.float64)
    prices, price_ses = mc_call_prices(s_terminal, s0, moneyness, maturity=maturity, r=r)
    forward = s0 * np.exp(r * maturity)
    strikes = forward * np.exp(moneyness)
    implied = np.array(
        [
            implied_vol(float(price), s0, float(strike), maturity, r)
            for price, strike in zip(prices, strikes, strict=True)
        ]
    )
    vegas = np.array(
        [
            float(vega(s0, float(strike), maturity, float(volatility), r))
            if np.isfinite(volatility) and volatility > 0
            else 0.0
            for strike, volatility in zip(strikes, implied, strict=True)
        ]
    )
    ok = np.isfinite(implied) & (implied > 0) & np.isfinite(vegas) & (vegas > 1e-12)
    implied_ses = np.full_like(implied, np.nan)
    implied_ses[ok] = price_ses[ok] / vegas[ok]
    implied[~ok] = np.nan
    return pd.DataFrame(
        {
            "k": moneyness,
            "price": prices,
            "price_se": price_ses,
            "iv": implied,
            "iv_se": implied_ses,
            "ok": ok,
        }
    )


def surface_from_terminals(
    s_by_maturity: Mapping[float, ArrayLike],
    s0: float,
    log_moneyness: ArrayLike | Sequence[float],
    *,
    r: float = 0.0,
) -> pd.DataFrame:
    """Combine terminal samples at several maturities into one surface table."""
    if not s_by_maturity:
        raise ValueError("s_by_maturity cannot be empty")
    frames: list[pd.DataFrame] = []
    for maturity in sorted(s_by_maturity):
        frame = smile_from_terminals(
            s_by_maturity[maturity],
            s0,
            log_moneyness,
            maturity=float(maturity),
            r=r,
        )
        frame.insert(0, "maturity", float(maturity))
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
