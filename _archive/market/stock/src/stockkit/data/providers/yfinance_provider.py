"""yfinance-backed data provider with DuckDB caching.

Public API:
    get_prices(symbol, start=None, end=None, period="5y", use_cache=True) -> DataFrame
    get_info(symbol) -> dict
    get_financials(symbol) -> dict[str, DataFrame]
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import yfinance as yf

from stockkit.data import cache
from stockkit.data.symbols import normalize_symbol

_DEFAULT_PERIOD = "5y"


def _yf_download(
    symbol: str, start: str | None, end: str | None, period: str | None
) -> pd.DataFrame:
    """Pull from yfinance and return canonical column-named DataFrame."""
    kwargs: dict[str, Any] = {"auto_adjust": False, "progress": False}
    if start or end:
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
    else:
        kwargs["period"] = period or _DEFAULT_PERIOD

    df = yf.download(symbol, **kwargs)
    if df is None or df.empty:
        return pd.DataFrame()

    # yfinance can return MultiIndex columns when downloading single symbol now.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    keep = ["open", "high", "low", "close", "adj_close", "volume"]
    df = df[[c for c in keep if c in df.columns]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "date"
    return df


def get_prices(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    period: str = _DEFAULT_PERIOD,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Return OHLCV DataFrame indexed by date.

    Caching strategy: when use_cache is True, we serve from DuckDB cache first
    and only request the missing tail (last_cached_date+1 .. today).
    """
    sym = normalize_symbol(symbol)

    if not use_cache:
        return _yf_download(sym, start, end, period)

    last = cache.latest_cached_date(sym)
    today = pd.Timestamp(datetime.utcnow().date())

    need_full = last is None
    if need_full:
        fresh = _yf_download(sym, start, end, period)
        if not fresh.empty:
            cache.upsert_prices(sym, fresh)
    elif last < today - pd.Timedelta(days=1):
        # Fetch only the tail since last cached date.
        tail_start = (last + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        tail = _yf_download(sym, start=tail_start, end=None, period=None)
        if not tail.empty:
            cache.upsert_prices(sym, tail)

    df = cache.read_prices(sym, start=start, end=end)
    if start is None and end is None and df.empty is False:
        # Slice to requested period if user passed period only
        if period and period != "max":
            cutoff = _period_to_start(period)
            if cutoff is not None:
                df = df.loc[df.index >= cutoff]
    return df


def _period_to_start(period: str) -> pd.Timestamp | None:
    period = period.strip().lower()
    today = pd.Timestamp(datetime.utcnow().date())
    units = {"d": 1, "mo": 30, "y": 365}
    # Quick parser: 1d/5d/1mo/6mo/1y/5y/10y
    try:
        if period.endswith("mo"):
            n = int(period[:-2])
            return today - pd.Timedelta(days=n * units["mo"])
        if period.endswith("y"):
            n = int(period[:-1])
            return today - pd.Timedelta(days=n * units["y"])
        if period.endswith("d"):
            n = int(period[:-1])
            return today - pd.Timedelta(days=n)
    except ValueError:
        return None
    return None


def get_info(symbol: str) -> dict[str, Any]:
    """Return ticker info dict. Network-dependent; not cached yet."""
    sym = normalize_symbol(symbol)
    t = yf.Ticker(sym)
    try:
        info = t.info or {}
    except Exception:
        info = {}
    return dict(info)


def get_financials(symbol: str) -> dict[str, pd.DataFrame]:
    """Return income / balance / cashflow DataFrames (annual)."""
    sym = normalize_symbol(symbol)
    t = yf.Ticker(sym)
    out: dict[str, pd.DataFrame] = {}
    for key, attr in (
        ("income", "income_stmt"),
        ("balance", "balance_sheet"),
        ("cashflow", "cashflow"),
        ("income_q", "quarterly_income_stmt"),
        ("balance_q", "quarterly_balance_sheet"),
        ("cashflow_q", "quarterly_cashflow"),
    ):
        try:
            df = getattr(t, attr)
            out[key] = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        except Exception:
            out[key] = pd.DataFrame()
    return out
