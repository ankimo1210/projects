"""Binance public-data connector — free crypto daily OHLCV klines (no key).

Full OHLCV (unlike the free CoinGecko price-only endpoint). Symbols map to USDT
pairs by default (``btc`` -> ``BTCUSDT``).
"""

from __future__ import annotations

import pandas as pd
import requests

from ..base import Connector

_PAIRS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT", "bnb": "BNBUSDT", "xrp": "XRPUSDT"}


def _pair(symbol: str) -> str:
    s = symbol.upper().replace("-USD", "").replace("USD", "")
    return _PAIRS.get(symbol.lower(), f"{s}USDT")


class BinanceConnector(Connector):
    source = "binance"
    BASE = "https://api.binance.com/api/v3/klines"

    def _download(self, symbol, start, end, *, pair: str | None = None, **_) -> pd.DataFrame:
        sym = pair or _pair(symbol)
        rows: list[list] = []
        cur = int(pd.Timestamp(start).timestamp() * 1000)
        end_ms = int(pd.Timestamp(end).timestamp() * 1000)
        while cur < end_ms:
            params = {"symbol": sym, "interval": "1d", "startTime": cur, "limit": 1000}
            r = requests.get(self.BASE, params=params, timeout=30)
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            cur = batch[-1][0] + 86_400_000
            if len(batch) < 1000:
                break
        return pd.DataFrame(rows)

    def normalize(self, raw: pd.DataFrame, symbol: str, **_) -> pd.DataFrame:
        if raw.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
        df = raw.iloc[:, :6].copy()
        df.columns = ["ms", "open", "high", "low", "close", "volume"]
        df["date"] = pd.to_datetime(df["ms"], unit="ms").dt.normalize()
        df = df.set_index("date").sort_index()
        out = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
        out["adj_close"] = out["close"]
        return out
