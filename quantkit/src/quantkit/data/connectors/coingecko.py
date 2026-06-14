"""CoinGecko connector — crypto daily prices (free demo key).

The ``market_chart/range`` endpoint returns prices only (no full OHLC), so
``open/high/low`` are left NaN and ``close``/``adj_close`` carry the daily price.

NOTE: CoinGecko's public API now requires a free **demo** API key (sent as the
``x-cg-demo-api-key`` header); without it the endpoint returns 401. Set
``COINGECKO_API_KEY`` or pass ``api_key=``. For a no-key crypto source with full
OHLCV, prefer :class:`~quantkit.data.connectors.binance.BinanceConnector`.
"""

from __future__ import annotations

import pandas as pd
import requests

from ...utils.config import env
from ..base import Connector

_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "btc-usd": "bitcoin",
    "eth-usd": "ethereum",
}


def _coin_id(symbol: str) -> str:
    return _IDS.get(symbol.lower(), symbol.lower())


class CoinGeckoConnector(Connector):
    source = "coingecko"
    BASE = "https://api.coingecko.com/api/v3"

    def __init__(self, *a, api_key: str | None = None, **kw):
        kw.setdefault("rate_limit_s", 2.5)  # free tier is rate-limited
        super().__init__(*a, **kw)
        self.api_key = api_key or env("COINGECKO_API_KEY")

    def _download(self, symbol, start, end, *, coin_id: str | None = None, **_) -> pd.DataFrame:
        cid = coin_id or _coin_id(symbol)
        params = {
            "vs_currency": "usd",
            "from": int(pd.Timestamp(start).timestamp()),
            "to": int(pd.Timestamp(end).timestamp()),
        }
        headers = {"x-cg-demo-api-key": self.api_key} if self.api_key else {}
        r = requests.get(
            f"{self.BASE}/coins/{cid}/market_chart/range",
            params=params,
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        prices = r.json().get("prices", [])
        return pd.DataFrame(prices, columns=["ms", "price"])

    def normalize(self, raw: pd.DataFrame, symbol: str, **_) -> pd.DataFrame:
        df = raw.copy()
        df["date"] = pd.to_datetime(df["ms"], unit="ms").dt.normalize()
        # one row per day (last price of the day)
        s = df.groupby("date")["price"].last()
        out = pd.DataFrame(index=s.index)
        out.index.name = "date"
        out["open"] = pd.NA
        out["high"] = pd.NA
        out["low"] = pd.NA
        out["close"] = s.values
        out["adj_close"] = s.values
        out["volume"] = pd.NA
        return out
