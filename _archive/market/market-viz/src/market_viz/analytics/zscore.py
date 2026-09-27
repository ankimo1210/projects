"""Z-score and percentile calculations."""

from __future__ import annotations

import pandas as pd


def rolling_zscore(series: pd.Series, window: int = 60) -> pd.Series:
    mu = series.rolling(window).mean()
    sigma = series.rolling(window).std()
    return (series - mu) / sigma.replace(0, float("nan"))


def rolling_percentile(series: pd.Series, window: int = 252) -> pd.Series:
    """Percentile rank within rolling window (0-100)."""
    return series.rolling(window).rank(pct=True) * 100


def build_zscore_matrix(
    prices_df: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [20, 60, 252]
    if prices_df.empty or "timestamp" not in prices_df.columns:
        return pd.DataFrame()
    pivot = prices_df.pivot(index="timestamp", columns="ticker", values="close").sort_index()
    rows: list[dict] = []
    for ticker in pivot.columns:
        s = pivot[ticker].dropna()
        if s.empty:
            continue
        row: dict = {"ticker": ticker}
        for w in windows:
            if len(s) >= w:
                z = rolling_zscore(s, window=w)
                pct = rolling_percentile(s, window=w)
                row[f"zscore_{w}d"] = z.iloc[-1]
                row[f"pct_{w}d"] = pct.iloc[-1]
        rows.append(row)
    return pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()
