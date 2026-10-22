"""Closes known at the as-of time, market caps in dollars, and the layer rule (spec 3.1)."""

from __future__ import annotations

import pytest
from portfolio_analyzer.ai_bubble.universe import (
    last_final_close,
    market_cap_usd,
    select_universe,
    shares_at,
)

AS_OF = "2026-10-21T00:00:00Z"  # 20:00 New York on the 20th, 09:00 Tokyo on the 21st


def test_us_close_of_the_previous_session_is_final_and_a_live_bar_is_not():
    bars = [("2026-10-19", 100.0), ("2026-10-20", 101.0), ("2026-10-21", 150.0)]
    assert last_final_close(bars, "NVDA", AS_OF) == ("2026-10-20", 101.0)


def test_tokyo_bar_is_final_only_after_the_close():
    bars = [("2026-10-19", 10.0), ("2026-10-20", 11.0)]
    assert last_final_close(bars, "8035.T", AS_OF) == ("2026-10-20", 11.0)
    # 14:00 JST on the 20th: that day's bar is still moving
    assert last_final_close(bars, "8035.T", "2026-10-20T05:00:00Z") == ("2026-10-19", 10.0)


def test_fx_bar_is_used_from_the_next_utc_day():
    bars = [("2026-10-20", 150.0), ("2026-10-21", 151.0)]
    assert last_final_close(bars, "JPY=X", AS_OF) == ("2026-10-20", 150.0)


def test_missing_closes_are_skipped_and_no_close_is_an_error():
    assert last_final_close([("2026-10-19", 9.0), ("2026-10-20", None)], "AMD", AS_OF) == (
        "2026-10-19",
        9.0,
    )
    with pytest.raises(ValueError, match="no final close"):
        last_final_close([("2026-10-21", 1.0)], "AMD", AS_OF)


def test_market_cap_converts_yen_and_adr_ratios():
    assert market_cap_usd(price=30_000.0, shares=450e6, currency="JPY", jpy_per_usd=150.0) == 90e9
    # one ADR = five ordinary shares
    assert market_cap_usd(price=300.0, shares=25e9, currency="USD", adr_ratio=5) == 1.5e12


LAYERS = [
    {"id": "buyers", "candidates": ["A", "B"], "take": 2},
    {"id": "design", "candidates": ["C", "D", "E"], "take": 2},
]


def test_ranked_layer_takes_the_largest_and_full_layers_take_all():
    caps = {"C": 5.0, "D": 9.0, "E": 7.0}
    out = select_universe(LAYERS, caps, must_include=[])
    assert out == {"buyers": ["A", "B"], "design": ["D", "E"]}


def test_must_include_survives_a_ranked_layer():
    caps = {"C": 5.0, "D": 9.0, "E": 7.0}
    out = select_universe(LAYERS, caps, must_include=["C"])
    assert out["design"] == ["D", "E", "C"]


def test_a_ranked_layer_without_every_cap_cannot_be_ranked():
    with pytest.raises(ValueError, match="E"):
        select_universe(LAYERS, {"C": 5.0, "D": 9.0}, must_include=[])


def test_a_split_after_the_count_date_scales_the_count():
    # Tokyo Electron: counted at 2026-06-30, 1:5 split ex 2026-09-29
    shares, applied = shares_at(454_651_196, "2026-06-30", [("2026-09-29", 5.0)])
    assert shares == 454_651_196 * 5
    assert applied == [("2026-09-29", 5.0)]


def test_a_split_before_the_count_date_is_already_in_the_count():
    # KLA: 1:10 ex 2026-06-12, cover page count dated 2026-08-03
    assert shares_at(1_306_546_783, "2026-08-03", [("2026-06-12", 10.0)]) == (1_306_546_783, [])


def test_every_later_split_applies_because_the_price_series_is_adjusted_for_it():
    # yfinance closes are divided by every split recorded up to retrieval, also
    # those after the close date, so the count must carry the same splits: the
    # product (price x count) is then the market cap of the close date.
    adjusted_close = 30.0  # raw close 60 before a 1:2 split made after the close date
    shares, _ = shares_at(100, "2026-06-30", [("2026-10-22", 2.0)])
    assert adjusted_close * shares == 60.0 * 100
