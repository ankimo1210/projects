"""Stooq connector — the PRIMARY source for long daily OHLCV history (free, no key).

Downloads the daily CSV from stooq.com. US tickers map to ``<sym>.us`` unless an
explicit ``stooq_symbol`` is given. (Prior art: stockkit's stooq_provider.)
"""

from __future__ import annotations

import io
from typing import ClassVar

import pandas as pd
import requests

from ..base import Connector


def _stooq_symbol(symbol: str) -> str:
    s = symbol.lower()
    if "." in s or s.startswith("^"):
        return s
    return f"{s}.us"


class StooqConnector(Connector):
    source = "stooq"
    BASE = "https://stooq.com/q/d/l/"
    HEADERS: ClassVar[dict[str, str]] = {"User-Agent": "Mozilla/5.0 (quantkit research platform)"}

    def _download(
        self, symbol, start, end, *, stooq_symbol: str | None = None, **_
    ) -> pd.DataFrame:
        sym = stooq_symbol or _stooq_symbol(symbol)
        params = {
            "s": sym,
            "d1": pd.Timestamp(start).strftime("%Y%m%d"),
            "d2": pd.Timestamp(end).strftime("%Y%m%d"),
            "i": "d",
        }
        r = requests.get(self.BASE, params=params, headers=self.HEADERS, timeout=30)
        r.raise_for_status()
        text = r.text.strip()
        low = text.lower()
        if not text or low.startswith("<") or "no data" in low or "javascript" in low:
            # Stooq sometimes serves an anti-bot / JavaScript-verification page
            # instead of CSV; treat it as unavailable so get_prices() falls back.
            raise ValueError(f"stooq: no CSV for {sym} (anti-bot page or no data)")
        return pd.read_csv(io.StringIO(text))

    def normalize(self, raw: pd.DataFrame, symbol: str, **_) -> pd.DataFrame:
        df = raw.rename(columns=str.lower)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        out = pd.DataFrame(index=df.index)
        for col in ("open", "high", "low", "close", "volume"):
            out[col] = pd.to_numeric(df[col], errors="coerce") if col in df else pd.NA
        # stooq daily close is split/dividend adjusted for most series; we expose
        # it as adj_close too and flag the assumption in metadata/README.
        out["adj_close"] = out["close"]
        return out
