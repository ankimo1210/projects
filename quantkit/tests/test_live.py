"""Live network smoke tests — REAL fetches against the no-key sources.

Skipped by default; run with ``QUANTKIT_LIVE=1`` (and network access):

    QUANTKIT_LIVE=1 uv run pytest quantkit/tests/test_live.py -q

These verify the connectors end-to-end against the live APIs (not fixtures). They
are deselected from the normal suite so offline ``make test`` stays deterministic.
Key-gated sources (FRED / J-Quants / e-Stat / CoinGecko) are only run when their
credential is present.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("QUANTKIT_LIVE"), reason="live network test; set QUANTKIT_LIVE=1 to run"
)


def test_live_sec_edgar_point_in_time():
    from quantkit.data.fundamentals import SecEdgarConnector, fundamental_as_of

    c = SecEdgarConnector(user_agent="quantkit-research live test (kikeuchi1210@gmail.com)")
    facts = c.fetch_facts(320193)  # Apple
    assert facts.get("entityName")
    obs = SecEdgarConnector.concept_observations(facts, "NetIncomeLoss")
    assert len(obs) > 10
    # FY2023 net income (~$97B) was filed by 2024-01-01 -> visible point-in-time
    assert fundamental_as_of(obs, "2024-01-01") > 5e10


def test_live_yfinance_prices():
    from quantkit.data import get_prices

    r = get_prices("SPY", "2024-01-01", "2024-02-01", source="yfinance")
    assert r.quality.rows > 15 and "close" in r.data


def test_live_auto_falls_back_to_yfinance():
    from quantkit.data import get_prices

    r = get_prices("SPY", "2024-01-01", "2024-02-01")  # stooq JS-wall -> yfinance
    assert r.source in {"stooq", "yfinance"} and r.quality.rows > 15


def test_live_binance_ohlcv():
    from quantkit.data import get_prices

    r = get_prices("btc", "2024-01-01", "2024-01-31", source="binance")
    assert r.quality.rows > 25 and (r.data["high"] >= r.data["low"]).all()


def test_live_us_treasury_yields():
    from quantkit.macro import TreasuryConnector

    df = TreasuryConnector().fetch("10y", "2024-01-01", "2024-03-01")
    assert len(df) > 30
    assert 0.0 < float(df["value"].dropna().iloc[-1]) < 15.0  # a plausible 10y yield (%)


@pytest.mark.skipif(not os.environ.get("FRED_API_KEY"), reason="needs FRED_API_KEY")
def test_live_fred_point_in_time():
    from quantkit.macro import FredConnector, as_of

    f = FredConnector().fetch("us_cpi", "2015-01-01", point_in_time=True)
    assert len(as_of(f, "2020-03-01")) > 0


@pytest.mark.skipif(not os.environ.get("COINGECKO_API_KEY"), reason="needs COINGECKO_API_KEY")
def test_live_coingecko_prices():
    from quantkit.data import get_prices

    r = get_prices("btc", "2024-01-01", "2024-01-31", source="coingecko")
    assert r.quality.rows > 25
