"""US stock index constituent fetchers (DJIA, S&P 500, NASDAQ-100).

DJIA  : 30 stocks, price-weighted (like Nikkei 225)
SP500 : 503 stocks, cap-weighted
NDX100: 101 stocks, cap-weighted (modified, tech-tilted)
"""

from __future__ import annotations

import os
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

_DATA_DIR = Path(os.environ.get("STOCKKIT_DATA_DIR", Path(__file__).resolve().parents[3] / "_data"))

_SOURCES = {
    "DJIA": {
        "url": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
        "symbol_col": "Symbol",
        "name_col": "Company",
        "weighting": "price",  # DJIA is price-weighted
    },
    "SP500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "symbol_col": "Symbol",
        "name_col": "Security",
        "weighting": "marketcap",
    },
    "NDX100": {
        "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "symbol_col": "Ticker",
        "name_col": "Company",
        "weighting": "marketcap",
    },
}


def _csv_path(index: str) -> Path:
    return _DATA_DIR / f"us_index_{index.lower()}.csv"


def fetch_constituents(index: str) -> pd.DataFrame:
    """Scrape constituents from Wikipedia for the given index code."""
    if index not in _SOURCES:
        raise ValueError(f"Unknown index: {index}. Choose from {list(_SOURCES)}")
    src = _SOURCES[index]

    r = requests.get(src["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(StringIO(r.text), header=0)

    sym_col = src["symbol_col"]
    name_col = src["name_col"]

    found = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if sym_col in cols and name_col in cols and len(t) >= 25:
            found = t
            break
    if found is None:
        raise RuntimeError(f"{index}: constituent table not found on Wikipedia")

    df = found[[sym_col, name_col]].copy()
    df.columns = ["ticker", "name"]
    # Wikipedia sometimes uses BRK.B → yfinance uses BRK-B
    df["ticker"] = df["ticker"].astype(str).str.replace(".", "-", regex=False)
    df = df.drop_duplicates(subset=["ticker"]).reset_index(drop=True)
    df["index"] = index
    df["weighting"] = src["weighting"]

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_csv_path(index), index=False)
    return df


def load_constituents(index: str, refresh: bool = False) -> pd.DataFrame:
    """Load constituents from CSV cache, fetching from Wikipedia on first call."""
    path = _csv_path(index)
    if refresh or not path.exists():
        return fetch_constituents(index)
    return pd.read_csv(path)


def get_index_meta(index: str) -> dict:
    """Return index metadata: yfinance benchmark ticker, weighting method, etc."""
    meta = {
        "DJIA": {
            "name": "Dow Jones Industrial Average",
            "yf_index": "^DJI",
            "yf_etf": "DIA",
            "yf_futures": "YM=F",
            "weighting": "price",
        },
        "SP500": {
            "name": "S&P 500",
            "yf_index": "^GSPC",
            "yf_etf": "SPY",
            "yf_futures": "ES=F",
            "weighting": "marketcap",
        },
        "NDX100": {
            "name": "NASDAQ-100",
            "yf_index": "^NDX",
            "yf_etf": "QQQ",
            "yf_futures": "NQ=F",
            "weighting": "marketcap",
        },
    }
    return meta.get(index, {})
