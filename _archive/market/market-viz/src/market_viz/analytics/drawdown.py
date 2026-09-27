"""Drawdown calculations."""

from __future__ import annotations

import pandas as pd


def drawdown_series(close: pd.Series) -> pd.Series:
    peak = close.cummax().replace(0, float("nan"))
    return (close - peak) / peak


def max_drawdown(close: pd.Series) -> float:
    return drawdown_series(close).min()


def current_drawdown(close: pd.Series) -> float:
    return drawdown_series(close).iloc[-1]


def build_drawdown_matrix(prices_df: pd.DataFrame) -> pd.DataFrame:
    if prices_df.empty or "timestamp" not in prices_df.columns:
        return pd.DataFrame()
    pivot = prices_df.pivot(index="timestamp", columns="ticker", values="close").sort_index()
    rows: list[dict] = []
    for ticker in pivot.columns:
        s = pivot[ticker].dropna()
        if s.empty:
            continue
        rows.append(
            {
                "ticker": ticker,
                "current_dd": current_drawdown(s),
                "max_dd": max_drawdown(s),
            }
        )
    return pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()
