"""Correlation calculations."""

from __future__ import annotations

import pandas as pd
import numpy as np


def build_return_pivot(prices_df: pd.DataFrame) -> pd.DataFrame:
    if prices_df.empty or "timestamp" not in prices_df.columns:
        return pd.DataFrame()
    pivot = prices_df.pivot(index="timestamp", columns="ticker", values="close").sort_index()
    return pivot.pct_change().dropna(how="all")


def static_correlation(prices_df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    ret = build_return_pivot(prices_df)
    return ret.tail(window).corr()


def rolling_correlation(
    prices_df: pd.DataFrame,
    ticker_a: str,
    ticker_b: str,
    window: int = 20,
) -> pd.Series:
    ret = build_return_pivot(prices_df)
    if ticker_a not in ret.columns or ticker_b not in ret.columns:
        return pd.Series(dtype=float)
    # 両銘柄に値がある行のみ使う（異なるカレンダー対応）
    pair = ret[[ticker_a, ticker_b]].dropna()
    if pair.empty:
        return pd.Series(dtype=float)
    return pair[ticker_a].rolling(window, min_periods=max(5, window // 2)).corr(pair[ticker_b])


def latest_correlations(prices_df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Full correlation matrix for the last `window` trading days."""
    return static_correlation(prices_df, window=window)
