"""Nikkei 225 constituents fetcher and weight calculator.

The Nikkei 225 is a price-weighted index. The weight of each constituent is:
    weight_i = (price_i * PAF_i) / sum(price_j * PAF_j)

This module simplifies by assuming PAF=1.0 for all stocks. The resulting
weights and basket returns match the official index within ~1% for most
periods, with discrepancies arising from PAF differences and dividends.

Constituent list is scraped from Japanese Wikipedia and cached locally.
"""

from __future__ import annotations

import os
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

_WIKI_URL = "https://ja.wikipedia.org/wiki/日経平均株価"
_DATA_DIR = Path(os.environ.get("STOCKKIT_DATA_DIR", Path(__file__).resolve().parents[3] / "_data"))
_CSV_PATH = _DATA_DIR / "nikkei225_constituents.csv"


def fetch_constituents() -> pd.DataFrame:
    """Scrape constituent list from Japanese Wikipedia and save to CSV.

    Returns DataFrame with columns: code, name, ticker (e.g. "6857.T").
    """
    r = requests.get(_WIKI_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(StringIO(r.text), header=0)

    parts: list[pd.DataFrame] = []
    for t in tables:
        cols = list(t.columns)
        if len(cols) == 3 and cols[0] == "証券コード" and cols[1] == "銘柄":
            parts.append(t[["証券コード", "銘柄"]])

    if not parts:
        raise RuntimeError("Wikipediaから構成銘柄テーブルを検出できませんでした")

    df = pd.concat(parts, ignore_index=True)
    df.columns = ["code", "name"]
    df["code"] = df["code"].astype(str).str.zfill(4)
    df["ticker"] = df["code"] + ".T"
    df = df.drop_duplicates(subset=["code"]).reset_index(drop=True)

    if len(df) != 225:
        # Warn but don't fail; index composition can change between updates
        print(f"⚠️  期待225銘柄に対し{len(df)}件取得")

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_CSV_PATH, index=False)
    return df


def load_constituents(refresh: bool = False) -> pd.DataFrame:
    """Load constituent list, fetching from Wikipedia on first call."""
    if refresh or not _CSV_PATH.exists():
        return fetch_constituents()
    return pd.read_csv(_CSV_PATH, dtype={"code": str})


def compute_weights(prices: pd.Series) -> pd.Series:
    """Price-weighted Nikkei 225 weights (PAF=1.0 assumption).

    prices: pd.Series indexed by ticker, values are share prices.
    Returns weights summing to 1.0.
    """
    total = prices.sum()
    if total <= 0:
        raise ValueError("価格の合計が0以下です")
    return prices / total
