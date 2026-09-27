"""Stooq data provider (direct HTTP, no pandas_datareader).

Covers indices not available in yfinance (e.g. TOPIX ^tpx).
Returns OHLCV DataFrames compatible with the existing DuckDB prices cache.

Required env (.env):
    STOOQ_API_KEY=<your key>
    Get a free key at: https://stooq.com/q/d/?s=^tpx&get_apikey
    (Enter the captcha; copy the apikey from the resulting URL)

Notable tickers:
    ^tpx   - TOPIX Index (Tokyo Stock Exchange)
    ^nkx   - Nikkei 225
    ^spx   - S&P 500
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

from stockkit.data import cache as _cache

_STOOQ_CSV = "https://stooq.com/q/d/l/"
_DEFAULT_YEARS = 5


class StooqError(RuntimeError):
    pass


def _api_key() -> str:
    load_dotenv()
    key = os.environ.get("STOOQ_API_KEY", "")
    if not key:
        raise StooqError(
            "STOOQ_API_KEY not set in .env. "
            "Get a free key at https://stooq.com/q/d/?s=^tpx&get_apikey"
        )
    return key


def is_configured() -> bool:
    load_dotenv()
    return bool(os.environ.get("STOOQ_API_KEY"))


def stooq_get_prices(
    ticker: str,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch OHLCV from Stooq and cache in DuckDB prices table."""
    sym = ticker.upper()

    if not start:
        start = (datetime.utcnow() - timedelta(days=365 * _DEFAULT_YEARS)).strftime("%Y-%m-%d")
    if not end:
        end = datetime.utcnow().strftime("%Y-%m-%d")

    if use_cache:
        last = _cache.latest_cached_date(sym)
        if last is not None and last >= pd.Timestamp(end) - pd.Timedelta(days=2):
            return _cache.read_prices(sym, start=start, end=end)

    df = _stooq_download(ticker, start, end)
    if df.empty:
        return df

    if use_cache:
        _cache.upsert_prices(sym, df)
        return _cache.read_prices(sym, start=start, end=end)
    return df


def _stooq_download(ticker: str, start: str, end: str) -> pd.DataFrame:
    d1 = start.replace("-", "")
    d2 = end.replace("-", "")
    params = {"s": ticker, "d1": d1, "d2": d2, "i": "d", "apikey": _api_key()}
    r = requests.get(_STOOQ_CSV, params=params, timeout=30)
    if r.status_code >= 400 or not r.text.strip().startswith("Date"):
        raise StooqError(f"Stooq returned unexpected response for {ticker}: {r.text[:200]}")

    df = pd.read_csv(io.StringIO(r.text))
    df = df.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df["adj_close"] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = float("nan")
    keep = ["open", "high", "low", "close", "adj_close", "volume"]
    return df[[c for c in keep if c in df.columns]]
