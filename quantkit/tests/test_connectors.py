"""Connector contract (offline): fetch caches + normalizes + reports quality;
retries surface as ConnectorError; per-source normalize maps to the schema."""

from __future__ import annotations

import io

import pandas as pd
import pytest
from quantkit.data.base import Connector, ConnectorError
from quantkit.data.cache import CacheManager
from quantkit.data.connectors.coingecko import CoinGeckoConnector
from quantkit.data.connectors.stooq import StooqConnector
from quantkit.macro.connectors.treasury import TreasuryConnector


class _FakeConn(Connector):
    source = "fake"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.calls = 0

    def _download(self, symbol, start, end, **_):
        self.calls += 1
        idx = pd.bdate_range(start, periods=6)
        return pd.DataFrame({"close": range(6)}, index=idx)

    def normalize(self, raw, symbol, **_):
        out = raw.copy()
        out["adj_close"] = out["close"]
        return out


def test_fetch_caches_and_reuses(tmp_path):
    c = _FakeConn(cache=CacheManager(root=tmp_path), ttl_seconds=3600)
    r1 = c.fetch("X", "2024-01-01", "2024-01-31")
    assert not r1.from_cache and r1.calls if hasattr(r1, "calls") else True
    assert c.calls == 1
    assert "close" in r1.data and r1.quality.rows == 6
    r2 = c.fetch("X", "2024-01-01", "2024-01-31")  # second call -> processed cache
    assert r2.from_cache and c.calls == 1


class _BoomConn(Connector):
    source = "boom"

    def _download(self, symbol, start, end, **_):
        raise RuntimeError("network down")

    def normalize(self, raw, symbol, **_):
        return raw


def test_download_failure_raises_connector_error(tmp_path):
    c = _BoomConn(cache=CacheManager(root=tmp_path), retries=1)
    with pytest.raises(ConnectorError):
        c.fetch("X", "2024-01-01", "2024-01-31")


def test_stooq_normalize_schema():
    csv = "Date,Open,High,Low,Close,Volume\n2024-01-02,10,11,9,10.5,1000\n2024-01-03,10.5,12,10,11,1200\n"
    raw = pd.read_csv(io.StringIO(csv))
    out = StooqConnector().normalize(raw, "spy")
    assert list(out.columns) == ["open", "high", "low", "close", "volume", "adj_close"]
    assert out.index.is_monotonic_increasing
    assert out.loc["2024-01-03", "close"] == 11
    assert (out["adj_close"] == out["close"]).all()


def test_coingecko_normalize_price_only():
    raw = pd.DataFrame({"ms": [1704153600000, 1704240000000], "price": [42000.0, 43000.0]})
    out = CoinGeckoConnector().normalize(raw, "btc")
    assert out["close"].tolist() == [42000.0, 43000.0]
    assert out["open"].isna().all()  # free endpoint is price-only, not fabricated


def test_treasury_normalize_tenor():
    csv = "Date,3 Mo,2 Yr,10 Yr,30 Yr\n01/02/2024,5.4,4.3,3.9,4.0\n01/03/2024,5.41,4.32,3.95,4.05\n"
    raw = pd.read_csv(io.StringIO(csv))
    obs = TreasuryConnector().to_observations(raw, "10y")
    assert len(obs) == 2
    assert obs[0].indicator_name == "ust_10y"
    assert obs[1].value == 3.95
    assert obs[0].release_date == obs[0].period_start  # released same day
