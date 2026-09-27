from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import Instrument, PriceBar
from market_research.prices import BarTiming, assess_bars, normalize_yfinance, select_bars_as_of

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
    bars = normalize_yfinance(
        original,
        INST,
        END + timedelta(hours=1),
        expected_provider_symbol="ACME",
        bar_timing={pd.Timestamp(END): BarTiming(END - timedelta(hours=7), END, True)},
    )
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
    bars = normalize_yfinance(
        raw,
        INST,
        END + timedelta(hours=1),
        expected_provider_symbol="ACME",
        bar_timing={pd.Timestamp(END): BarTiming(END - timedelta(hours=7), END, True)},
    )
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
    assert select_bars_as_of([replace(bar, is_final=False)], END + timedelta(days=1)) == ()


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


def test_timezone_aware_session_label_without_verified_bounds_is_rejected():
    label = pd.Timestamp("2026-09-25 00:00", tz="America/New_York")
    raw = pd.DataFrame({"Close": [100.0]}, index=pd.DatetimeIndex([label]))
    with pytest.raises(ValueError, match="bar_timing"):
        normalize_yfinance(
            raw,
            INST,
            datetime(2026, 9, 25, 14, tzinfo=UTC),
            expected_provider_symbol="ACME",
        )


def test_explicit_session_bounds_preserve_dst_and_finality():
    label = pd.Timestamp("2026-11-02 00:00", tz="America/New_York")
    start = datetime(2026, 11, 2, 14, 30, tzinfo=UTC)
    end = datetime(2026, 11, 2, 21, tzinfo=UTC)
    observed = end + timedelta(minutes=5)
    raw = pd.DataFrame({"Close": [100.0]}, index=pd.DatetimeIndex([label]))
    bars = normalize_yfinance(
        raw,
        INST,
        observed,
        expected_provider_symbol="ACME",
        bar_timing={label: BarTiming(start, end, is_final=True)},
    )
    assert len(bars) == 1
    assert bars[0].bar_start == start
    assert bars[0].bar_end == end
    assert bars[0].available_at == observed
    assert bars[0].is_final
    assert select_bars_as_of(bars, end) == ()
    assert select_bars_as_of(bars, observed) == bars


def test_provider_symbol_mismatch_is_rejected_but_explicit_alias_is_allowed():
    columns = pd.MultiIndex.from_tuples([("Close", "OTHER")])
    raw = pd.DataFrame([[100.0]], columns=columns, index=pd.DatetimeIndex([END]))
    timing = {pd.Timestamp(END): BarTiming(END - timedelta(hours=7), END, is_final=True)}
    with pytest.raises(ValueError, match="provider symbol"):
        normalize_yfinance(
            raw,
            INST,
            END + timedelta(hours=1),
            expected_provider_symbol="ACME",
            bar_timing=timing,
        )
    alias_raw = raw.rename(columns={"OTHER": "ACME.US"})
    bars = normalize_yfinance(
        alias_raw,
        INST,
        END + timedelta(hours=1),
        expected_provider_symbol="ACME.US",
        bar_timing=timing,
    )
    assert bars[0].instrument.instrument_id == "XNAS:ACME"
    assert bars[0].provider_symbol == "ACME.US"


def test_explicit_nonfinal_bar_stays_nonfinal_and_is_not_readable():
    raw = pd.DataFrame({"Close": [100.0]}, index=pd.DatetimeIndex([END]))
    bars = normalize_yfinance(
        raw,
        INST,
        END + timedelta(hours=1),
        expected_provider_symbol="ACME",
        bar_timing={pd.Timestamp(END): BarTiming(END - timedelta(hours=7), END, is_final=False)},
    )
    assert not bars[0].is_final
    assert select_bars_as_of(bars, END + timedelta(hours=1)) == ()


def test_intraday_snapshot_retains_partial_bar_and_audits_exclusion():
    from market_research.prices import price_view_as_of

    instrument = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
    today = pd.Timestamp("2026-09-25 00:00", tz="Asia/Tokyo")
    yesterday = today - pd.Timedelta(days=1)
    observed = datetime(2026, 9, 25, 5, tzinfo=UTC)  # 14:00 JST
    end = datetime(2026, 9, 25, 6, 30, tzinfo=UTC)
    raw = pd.DataFrame({"Close": [100.0, 101.0]}, index=[yesterday, today])
    bars = normalize_yfinance(
        raw,
        instrument,
        observed,
        expected_provider_symbol="7203.T",
        bar_timing={
            yesterday: BarTiming(
                end - timedelta(days=1, hours=6, minutes=30), end - timedelta(days=1), True
            ),
            today: BarTiming(end - timedelta(hours=6, minutes=30), end, False),
        },
    )
    view = price_view_as_of(bars, observed)
    assert [bar.close for bar in view.bars] == [100.0]
    assert [(row.bar.close, row.reason) for row in view.exclusions] == [(101.0, "non_final")]
    assert [bar.close for bar in price_view_as_of(bars, end + timedelta(days=1)).bars] == [100.0]
    final = replace(
        bars[1],
        is_final=True,
        close=102.0,
        available_at=end + timedelta(minutes=5),
        observed_at=end + timedelta(minutes=5),
        revision_id="final",
    )
    assert [
        bar.close for bar in price_view_as_of([*bars, final], end + timedelta(minutes=5)).bars
    ] == [100.0, 102.0]


def test_final_bar_still_cannot_be_available_before_its_close():
    with pytest.raises(ValueError, match="available_at"):
        sample_bar(available_at=END - timedelta(hours=1), observed_at=END - timedelta(hours=1))


def test_partial_bar_can_be_observed_during_its_interval():
    bar = sample_bar(
        is_final=False, available_at=END - timedelta(hours=1), observed_at=END - timedelta(hours=1)
    )
    assert bar.available_at < bar.bar_end
