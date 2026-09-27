from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import Instrument, PriceBar
from market_research.prices import assess_bars, normalize_yfinance, select_bars_as_of

END = datetime(2026, 9, 25, 20, tzinfo=UTC)
INST = Instrument("XNAS", "ACME", "USD", "America/New_York")


def sample_bar(close=100.0, **changes):
    values = dict(
        instrument=INST,
        provider="yfinance",
        interval="1d",
        bar_start=END - timedelta(days=1),
        bar_end=END,
        available_at=END + timedelta(minutes=5),
        observed_at=END + timedelta(hours=1),
        close=close,
        adjustment="raw",
        revision_id="v1",
    )
    values.update(changes)
    return PriceBar(**values)


def test_flat_raw_prices_do_not_pretend_to_be_adjusted():
    original = pd.DataFrame(
        {"Open": [99.0], "Close": [100.0], "Volume": [1000]}, index=pd.DatetimeIndex([END])
    )
    bars = normalize_yfinance(original, INST, END + timedelta(hours=1))
    assert [(b.close, b.adjustment, b.provider_symbol) for b in bars] == [(100.0, "raw", "ACME")]
    assert original.loc[END, "Close"] == 100.0


def test_multiindex_keeps_raw_and_unclassified_adjusted_separate():
    cols = pd.MultiIndex.from_tuples(
        [
            ("Open", "ACME"),
            ("High", "ACME"),
            ("Low", "ACME"),
            ("Close", "ACME"),
            ("Adj Close", "ACME"),
        ]
    )
    raw = pd.DataFrame(
        [[99.0, 101.0, 98.0, 100.0, 95.0]], columns=cols, index=pd.DatetimeIndex([END])
    )
    bars = normalize_yfinance(raw, INST, END + timedelta(hours=1))
    assert [(b.adjustment, b.close) for b in bars] == [("raw", 100.0), ("unknown", 95.0)]
    assert all(b.provider_symbol == "ACME" for b in bars)
    assert bars[1].open is None and bars[1].high is None and bars[1].low is None


def test_naive_daily_index_is_rejected_instead_of_guessing_market_close():
    raw = pd.DataFrame({"Close": [100.0]}, index=pd.DatetimeIndex([END.replace(tzinfo=None)]))
    with pytest.raises(ValueError, match="timezone-aware"):
        normalize_yfinance(raw, INST, END + timedelta(hours=1))


def test_adjustment_request_does_not_fall_back_to_raw():
    with pytest.raises(ValueError, match="adjustment"):
        select_bars_as_of([sample_bar()], END + timedelta(days=1), adjustment="total_return")


def test_later_revision_cannot_change_earlier_view():
    original = sample_bar()
    corrected = replace(
        original,
        close=101.0,
        revision_id="v2",
        available_at=END + timedelta(days=2),
        observed_at=END + timedelta(days=2),
    )
    assert [b.close for b in select_bars_as_of([original, corrected], END + timedelta(days=1))] == [
        100.0
    ]
    assert [b.close for b in select_bars_as_of([original, corrected], END + timedelta(days=3))] == [
        101.0
    ]


def test_duplicate_revision_and_open_bar_fail_closed():
    bar = sample_bar()
    with pytest.raises(ValueError, match="duplicate"):
        select_bars_as_of([bar, bar], END + timedelta(days=1))
    with pytest.raises(ValueError, match="non-final"):
        select_bars_as_of([replace(bar, is_final=False)], END + timedelta(days=1))


def test_extreme_value_is_flagged_without_rewriting_past():
    first = sample_bar()
    second = replace(
        first,
        bar_start=END,
        bar_end=END + timedelta(days=1),
        available_at=END + timedelta(days=1, minutes=5),
        observed_at=END + timedelta(days=1, hours=1),
        close=10.0,
        revision_id="v2",
    )
    before = assess_bars([first, second], END + timedelta(hours=2))
    after = assess_bars([first, second], END + timedelta(days=2))
    assert [(b.close, b.quality) for b in before] == [(100.0, "ok")]
    assert [(b.close, b.quality) for b in after] == [(100.0, "ok"), (10.0, "warn")]
    assert after[-1].quality_reasons == ("large_close_jump",)
    assert second.quality == "ok"


def test_same_symbol_from_two_providers_is_not_merged():
    original = sample_bar()
    other = replace(original, provider="stooq", revision_id="stooq-v1", close=99.0)
    result = select_bars_as_of([original, other], END + timedelta(days=1))
    assert {(b.provider, b.close) for b in result} == {("yfinance", 100.0), ("stooq", 99.0)}
