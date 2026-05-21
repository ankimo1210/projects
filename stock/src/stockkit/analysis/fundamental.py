"""Fundamental analysis helpers (yfinance-based)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from stockkit.data.providers.yfinance_provider import get_financials, get_info

# Map of "human key" -> yfinance info field(s) to try
_INFO_FIELDS = {
    "name": ["longName", "shortName"],
    "sector": ["sector"],
    "industry": ["industry"],
    "market_cap": ["marketCap"],
    "currency": ["currency"],
    "pe": ["trailingPE"],
    "forward_pe": ["forwardPE"],
    "pb": ["priceToBook"],
    "ps": ["priceToSalesTrailing12Months"],
    "peg": ["pegRatio"],
    "ev_ebitda": ["enterpriseToEbitda"],
    "roe": ["returnOnEquity"],
    "roa": ["returnOnAssets"],
    "dividend_yield": ["dividendYield"],
    "profit_margin": ["profitMargins"],
    "operating_margin": ["operatingMargins"],
    "revenue_growth": ["revenueGrowth"],
    "earnings_growth": ["earningsGrowth"],
    "debt_to_equity": ["debtToEquity"],
    "current_ratio": ["currentRatio"],
    "beta": ["beta"],
    "price": ["currentPrice", "regularMarketPrice"],
    "target_mean_price": ["targetMeanPrice"],
}


def snapshot(symbol: str) -> dict[str, Any]:
    """Return a flat dict of common fundamental metrics."""
    info = get_info(symbol)
    out: dict[str, Any] = {"symbol": symbol}
    for key, candidates in _INFO_FIELDS.items():
        out[key] = next((info[c] for c in candidates if info.get(c) is not None), None)
    return out


def snapshot_df(symbols: list[str]) -> pd.DataFrame:
    """Snapshot multiple symbols. Network-bound; one yfinance call per symbol."""
    rows = [snapshot(s) for s in symbols]
    return pd.DataFrame(rows).set_index("symbol")


def yoy_growth(financials: pd.DataFrame, row: str) -> pd.Series:
    """YoY growth of a given line (e.g. 'Total Revenue') from financials.

    yfinance returns columns as period-end timestamps in *descending* order;
    we sort ascending then pct_change.
    """
    if financials is None or financials.empty or row not in financials.index:
        return pd.Series(dtype=float)
    s = financials.loc[row].astype(float).sort_index()
    return s.pct_change()


def revenue_growth_history(symbol: str) -> pd.Series:
    fin = get_financials(symbol)
    return yoy_growth(fin.get("income", pd.DataFrame()), "Total Revenue")


def net_income_history(symbol: str) -> pd.Series:
    fin = get_financials(symbol)
    inc = fin.get("income", pd.DataFrame())
    if inc.empty or "Net Income" not in inc.index:
        return pd.Series(dtype=float)
    return inc.loc["Net Income"].astype(float).sort_index()
