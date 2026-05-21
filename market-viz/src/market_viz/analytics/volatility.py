"""Realized volatility calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd

ANN = 252


def realized_vol(close: pd.Series, window: int = 20, ann_factor: int = ANN) -> pd.Series:
    """Annualized realized volatility (rolling standard deviation of log returns)."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(ann_factor)


def vol_percentile(close: pd.Series, window: int = 20, lookback: int = 252) -> pd.Series:
    """Percentile rank of current vol vs lookback window."""
    rv = realized_vol(close, window=window)
    return rv.rolling(lookback).rank(pct=True)


def build_vol_matrix(
    prices_df: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [20, 60]
    if prices_df.empty or "timestamp" not in prices_df.columns:
        return pd.DataFrame()
    pivot = prices_df.pivot(index="timestamp", columns="ticker", values="close").sort_index()
    rows: list[dict] = []
    for ticker in pivot.columns:
        s = pivot[ticker].dropna()
        if len(s) < max(windows):
            continue
        row: dict = {"ticker": ticker}
        for w in windows:
            rv = realized_vol(s, window=w)
            row[f"vol_{w}d"] = rv.iloc[-1] if not rv.empty else None
        rows.append(row)
    return pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()
