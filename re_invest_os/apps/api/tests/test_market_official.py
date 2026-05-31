"""Market Grounding: 国交省 XIT001 実データのパース/集計テスト（ネットワーク非依存）。"""

from __future__ import annotations

import json
from pathlib import Path

from api.services.market.official import (
    MarketSnapshot,
    _price_per_sqm,
    get_area_market,
    recent_quarters,
    trade_price_stats,
)

FIX = Path(__file__).parent / "fixtures" / "market" / "xit001_shinjuku_2023q3.json"


def test_price_per_sqm() -> None:
    assert _price_per_sqm({"TradePrice": "100000000", "Area": "50"}) == 2_000_000
    assert _price_per_sqm({"TradePrice": "", "Area": "50"}) is None
    assert _price_per_sqm({"TradePrice": "1000", "Area": "0"}) is None
    assert _price_per_sqm({"TradePrice": None, "Area": "50"}) is None


def test_trade_price_stats_handbuilt() -> None:
    recs = [
        {"Type": "中古マンション等", "TradePrice": "100", "Area": "1"},
        {"Type": "中古マンション等", "TradePrice": "200", "Area": "1"},
        {"Type": "中古マンション等", "TradePrice": "300", "Area": "1"},
        {"Type": "宅地(土地)", "TradePrice": "9999", "Area": "1"},  # type_filter で除外
    ]
    s = trade_price_stats(recs)
    assert s.sample_count == 3  # 宅地は除外
    assert s.median_yen_per_sqm == 200
    assert s.p25_yen_per_sqm == 150
    assert s.p75_yen_per_sqm == 250


def test_trade_price_stats_empty() -> None:
    s = trade_price_stats([])
    assert s.sample_count == 0
    assert s.median_yen_per_sqm is None


def test_trade_price_stats_real_fixture() -> None:
    data = json.loads(FIX.read_text(encoding="utf-8"))
    s = trade_price_stats(data["data"])
    assert s.sample_count > 0
    # 都心マンションの ¥/㎡ レンジ（実データの sanity）
    assert 300_000 < s.median_yen_per_sqm < 5_000_000
    assert s.p25_yen_per_sqm <= s.median_yen_per_sqm <= s.p75_yen_per_sqm


def test_get_area_market_injected() -> None:
    data = json.loads(FIX.read_text(encoding="utf-8"))
    snap = get_area_market("13", "13104", get_fn=lambda path, params: data["data"])
    assert isinstance(snap, MarketSnapshot)
    assert snap.city_code == "13104"
    assert snap.trade is not None and snap.trade.sample_count > 0
    assert snap.source.startswith("国交省")
    assert snap.period is not None


def test_get_area_market_no_data_returns_none() -> None:
    snap = get_area_market("13", "13104", get_fn=lambda path, params: [])
    assert snap is None


def test_recent_quarters_lag() -> None:
    import datetime as dt

    qs = recent_quarters(dt.date(2026, 5, 31))
    # 2026Q2 から2四半期戻した 2025Q4 が先頭、新しい順
    assert qs[0] == (2025, 4)
    assert qs[1] == (2025, 3)
    assert all(1 <= q <= 4 for _, q in qs)
