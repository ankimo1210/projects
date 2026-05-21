"""Return calculations."""

from __future__ import annotations

import pandas as pd


def daily_returns(close: pd.Series) -> pd.Series:
    return close.pct_change()


def rolling_return(close: pd.Series, window: int) -> pd.Series:
    return close.pct_change(window)


def cumulative_return(close: pd.Series) -> pd.Series:
    r = daily_returns(close).fillna(0)
    return (1 + r).cumprod() - 1


def build_return_matrix(
    prices_df: pd.DataFrame,
    periods: list[int] = [1, 5, 20, 60, 252],
) -> pd.DataFrame:
    """pivot prices_df (timestamp, ticker, close) → return matrix per ticker."""
    if prices_df.empty or "timestamp" not in prices_df.columns:
        return pd.DataFrame()
    pivot = prices_df.pivot(index="timestamp", columns="ticker", values="close").sort_index()
    rows: list[dict] = []
    for ticker in pivot.columns:
        s = pivot[ticker].dropna()
        if s.empty:
            continue
        row: dict = {"ticker": ticker, "last_close": s.iloc[-1]}
        for p in periods:
            if len(s) > p:
                row[f"ret_{p}d"] = s.iloc[-1] / s.iloc[-1 - p] - 1
            else:
                row[f"ret_{p}d"] = None
        rows.append(row)
    return pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()
