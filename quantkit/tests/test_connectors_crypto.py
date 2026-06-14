"""Offline crypto-connector tests: symbol mapping (regression) and normalization.

Regression: a full pair like ``BTCUSDT`` must NOT have its inner ``USD`` stripped
(the old ``_pair`` produced ``BTCTUSDT`` -> Binance 400). CoinGecko now needs a
demo key; we check the header is attached when a key is configured.
"""

from __future__ import annotations

import pandas as pd
from quantkit.data.connectors.binance import BinanceConnector, _pair
from quantkit.data.connectors.coingecko import CoinGeckoConnector


def test_binance_pair_mapping():
    assert _pair("btc") == "BTCUSDT"  # alias
    assert _pair("BTCUSDT") == "BTCUSDT"  # already a full pair (regression: not BTCTUSDT)
    assert _pair("ETH-USD") == "ETHUSDT"
    assert _pair("sol") == "SOLUSDT"
    assert _pair("ETHBTC") == "ETHBTC"  # cross pair preserved


def test_binance_normalize_klines():
    raw = pd.DataFrame(
        [
            [1704067200000, "42000", "43000", "41500", "42800", "1000"],
            [1704153600000, "42800", "44000", "42700", "43900", "1200"],
        ]
    )
    out = BinanceConnector().normalize(raw, "btc")
    assert out["close"].tolist() == [42800.0, 43900.0]
    assert out["adj_close"].tolist() == [42800.0, 43900.0]
    assert out.index.is_monotonic_increasing


def test_coingecko_attaches_demo_key_header():
    c = CoinGeckoConnector(api_key="demo-123")
    assert c.api_key == "demo-123"
    # price-only normalize: open/high/low NaN, close carries the price
    raw = pd.DataFrame({"ms": [1704067200000, 1704153600000], "price": [42000.0, 43000.0]})
    out = c.normalize(raw, "btc")
    assert out["close"].tolist() == [42000.0, 43000.0]
    assert out["open"].isna().all()
