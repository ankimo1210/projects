"""Indicators keep numeric results and source context together."""

import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import Instrument, PriceBar, PriceGap
from market_research.prices import PriceExclusion
from market_research.research.dataset import PriceDataset

T1 = datetime(2026, 9, 24, 21, tzinfo=UTC)
IBM = Instrument("XNYS", "IBM", "USD", "America/New_York")
MSFT = Instrument("XNAS", "MSFT", "USD", "America/New_York")
TOYOTA = Instrument("XTKS", "7203", "USD", "Asia/Tokyo")


def _bar(
    instrument: Instrument,
    decision_at: datetime,
    close: float,
    *,
    quality: str = "ok",
    reasons: tuple[str, ...] = (),
) -> PriceBar:
    end = decision_at - timedelta(hours=1)
    return PriceBar(
        instrument,
        "yfinance",
        "1d",
        end - timedelta(hours=6),
        end,
        decision_at,
        decision_at,
        close,
        "raw",
        decision_at.isoformat(),
        quality=quality,
        quality_reasons=reasons,
    )


def test_indicator_values_match_hand_calculation():
    from market_research.research.indicators import IndicatorInput, indicator_table

    index = pd.date_range("2026-09-21 20:00", periods=5, freq="D", tz="UTC")
    frame = pd.DataFrame({"XNYS:IBM": [100, 110, 100, 120, 115]}, index=index)
    source = IndicatorInput(frame, "point_in_time", "USD", "raw")
    result = indicator_table(source, momentum_window=2, volatility_window=2, periods_per_year=252)
    row = result.loc["XNYS:IBM"]
    assert row["latest_close"] == 115
    assert row["momentum"] == pytest.approx(0.15)
    assert row["volatility_annualized"] == pytest.approx(
        ((0.2 + 1 / 24) / math.sqrt(2)) * math.sqrt(252)
    )
    assert row["drawdown"] == pytest.approx(-1 / 24)
    assert row["zscore"] == pytest.approx(-1.0)
    assert (row["mode"], row["currency"], row["adjustment"]) == (
        "point_in_time",
        "USD",
        "raw",
    )


def test_short_history_and_missing_latest_price_are_explicit():
    from market_research.research.indicators import IndicatorInput, indicator_table

    index = pd.date_range("2026-09-24 20:00", periods=2, freq="D", tz="UTC")
    short = IndicatorInput(
        pd.DataFrame({"XNYS:IBM": [100.0, 102.0]}, index=index),
        "point_in_time",
        "USD",
        "raw",
    )
    short_row = indicator_table(
        short, momentum_window=3, volatility_window=3, periods_per_year=252
    ).loc["XNYS:IBM"]
    assert short_row["latest_close"] == 102
    assert pd.isna(short_row["momentum"])
    assert pd.isna(short_row["volatility_annualized"])
    assert pd.isna(short_row["zscore"])
    assert short_row["missing_reason"] == "insufficient_history"

    missing = IndicatorInput(
        pd.DataFrame({"XNYS:IBM": [100.0, math.nan]}, index=index),
        "point_in_time",
        "USD",
        "raw",
    )
    missing_row = indicator_table(
        missing, momentum_window=1, volatility_window=2, periods_per_year=252
    ).loc["XNYS:IBM"]
    assert pd.isna(missing_row["latest_close"])
    assert pd.isna(missing_row["momentum"])
    assert missing_row["missing_reason"] == "missing_price"


def test_retro_history_keeps_warning_and_excludes_rejected_price():
    from market_research.research.indicators import close_history, indicator_table

    next_day = T1 + timedelta(days=1)
    dataset = PriceDataset(
        as_of=next_day,
        snapshot_ids=("ibm", "msft"),
        currency="USD",
        adjustment="raw",
        bars=(
            _bar(IBM, T1, 100),
            _bar(MSFT, T1, 50),
            _bar(IBM, next_day, 110, quality="warn", reasons=("large_close_jump",)),
            _bar(MSFT, next_day, 55, quality="reject", reasons=("manual_reject",)),
        ),
        gaps=(),
        exclusions=(),
    )
    source = close_history(dataset)
    assert source.mode == "retrospective"
    assert source.currency == "USD"
    assert source.prices.loc[next_day - timedelta(hours=1), "XNYS:IBM"] == 110
    assert pd.isna(source.prices.loc[next_day - timedelta(hours=1), "XNAS:MSFT"])
    summary = indicator_table(source, momentum_window=1, volatility_window=2, periods_per_year=252)
    assert summary.loc["XNYS:IBM", "quality_reasons"] == ("large_close_jump",)
    assert summary.loc["XNAS:MSFT", "quality_reasons"] == ("manual_reject",)
    assert summary.loc["XNAS:MSFT", "missing_reason"] == "rejected_price"


@pytest.mark.parametrize("missing_kind", ["gap", "non_final"])
def test_gap_or_open_bar_does_not_turn_old_close_into_current_metric(missing_kind):
    from market_research.research.indicators import close_history, indicator_table

    next_day = T1 + timedelta(days=1)
    gap = PriceGap(IBM, "yfinance", "IBM", "1d", next_day.date(), next_day, next_day, "raw")
    unfinished = replace(
        _bar(IBM, next_day, 101),
        bar_end=next_day + timedelta(hours=1),
        is_final=False,
    )
    dataset = PriceDataset(
        as_of=next_day,
        snapshot_ids=("ibm",),
        currency="USD",
        adjustment="raw",
        bars=(_bar(IBM, T1, 100),),
        gaps=(gap,) if missing_kind == "gap" else (),
        exclusions=(PriceExclusion(unfinished, "non_final"),)
        if missing_kind == "non_final"
        else (),
    )
    source = close_history(dataset)
    summary = indicator_table(source, momentum_window=1, volatility_window=2, periods_per_year=252)
    row = summary.loc["XNYS:IBM"]
    assert pd.isna(row["latest_close"])
    assert pd.isna(row["momentum"])
    assert row["missing_reason"] == missing_kind


def test_gap_only_snapshot_still_produces_an_explained_empty_summary():
    from market_research.research.indicators import close_history, indicator_table

    gap = PriceGap(IBM, "yfinance", "IBM", "1d", T1.date(), T1, T1, "raw")
    dataset = PriceDataset(
        as_of=T1,
        snapshot_ids=("ibm",),
        currency="USD",
        adjustment="raw",
        bars=(),
        gaps=(gap,),
        exclusions=(),
    )
    summary = indicator_table(
        close_history(dataset), momentum_window=1, volatility_window=2, periods_per_year=252
    )
    assert pd.isna(summary.loc["XNYS:IBM", "latest_close"])
    assert summary.loc["XNYS:IBM", "missing_reason"] == "gap"


def test_gap_only_asset_is_visible_beside_another_assets_bars():
    from market_research.research.indicators import close_history, indicator_table

    gap = PriceGap(MSFT, "yfinance", "MSFT", "1d", T1.date(), T1, T1, "raw")
    dataset = PriceDataset(
        as_of=T1,
        snapshot_ids=("ibm", "msft"),
        currency="USD",
        adjustment="raw",
        bars=(_bar(IBM, T1, 100),),
        gaps=(gap,),
        exclusions=(),
    )
    summary = indicator_table(
        close_history(dataset), momentum_window=1, volatility_window=2, periods_per_year=252
    )
    assert summary.index.tolist() == ["XNYS:IBM", "XNAS:MSFT"]
    assert pd.isna(summary.loc["XNAS:MSFT", "latest_close"])
    assert summary.loc["XNAS:MSFT", "missing_reason"] == "gap"


def test_display_panel_aligns_different_market_closes_by_session_date():
    from market_research.research.indicators import close_history

    bars = []
    for decision in (T1, T1 + timedelta(days=1)):
        tokyo_end = decision.replace(hour=6, minute=30)
        bars.extend(
            (
                _bar(IBM, decision, 100),
                PriceBar(
                    TOYOTA,
                    "yfinance",
                    "1d",
                    tokyo_end - timedelta(hours=6, minutes=30),
                    tokyo_end,
                    decision,
                    decision,
                    50,
                    "raw",
                    decision.isoformat(),
                ),
            )
        )
    dataset = PriceDataset(
        as_of=T1 + timedelta(days=1),
        snapshot_ids=("ibm", "toyota"),
        currency="USD",
        adjustment="raw",
        bars=tuple(bars),
        gaps=(),
        exclusions=(),
    )
    source = close_history(dataset)
    assert source.prices.shape == (2, 2)
    assert source.prices.index.tolist() == [
        T1 - timedelta(hours=1),
        T1 + timedelta(days=1) - timedelta(hours=1),
    ]
    assert source.prices.notna().all().all()


def test_display_history_rejects_mixed_source_contract():
    from market_research.research.indicators import close_history

    base = _bar(IBM, T1, 100)
    other_time = T1 + timedelta(days=1)
    for changed, word in (
        (replace(_bar(IBM, other_time, 101), provider="stooq"), "provider"),
        (replace(_bar(IBM, other_time, 101), adjustment="unknown"), "adjustment"),
        (
            replace(
                _bar(IBM, other_time, 101),
                instrument=replace(IBM, currency="JPY"),
            ),
            "currency",
        ),
        (replace(_bar(IBM, other_time, 101), interval="1h"), "interval"),
    ):
        dataset = PriceDataset(
            as_of=other_time,
            snapshot_ids=("one", "two"),
            currency="USD",
            adjustment="raw",
            bars=(base, changed),
            gaps=(),
            exclusions=(),
        )
        with pytest.raises(ValueError, match=word):
            close_history(dataset)


def test_display_history_rejects_bar_observed_after_its_as_of():
    from market_research.research.indicators import close_history

    dataset = PriceDataset(
        as_of=T1,
        snapshot_ids=("future",),
        currency="USD",
        adjustment="raw",
        bars=(_bar(IBM, T1 + timedelta(days=1), 100),),
        gaps=(),
        exclusions=(),
    )
    with pytest.raises(ValueError, match="future"):
        close_history(dataset)


def test_missing_session_is_independent_of_other_assets():
    from market_research.research.indicators import close_history, indicator_table

    middle = T1 + timedelta(days=1)
    last = T1 + timedelta(days=2)
    gap = PriceGap(IBM, "yfinance", "IBM", "1d", middle.date(), middle, middle, "raw")
    ibm_bars = (_bar(IBM, T1, 100), _bar(IBM, last, 110))
    single = PriceDataset(last, ("ibm",), "USD", "raw", ibm_bars, (gap,), ())
    paired = PriceDataset(
        last,
        ("ibm", "msft"),
        "USD",
        "raw",
        (*ibm_bars, _bar(MSFT, middle, 50)),
        (gap,),
        (),
    )
    single_input = close_history(single)
    paired_input = close_history(paired)
    assert len(single_input.prices) == 3
    assert pd.isna(single_input.prices.iloc[1]["XNYS:IBM"])
    for source in (single_input, paired_input):
        row = indicator_table(
            source, momentum_window=1, volatility_window=2, periods_per_year=252
        ).loc["XNYS:IBM"]
        assert pd.isna(row["momentum"])


def test_historical_gap_observed_later_keeps_display_dates_ordered():
    from market_research.research.indicators import close_history, indicator_table

    middle = T1 + timedelta(days=1)
    last = T1 + timedelta(days=2)
    gap = PriceGap(IBM, "yfinance", "IBM", "1d", middle.date(), last, last, "raw")
    dataset = PriceDataset(
        last,
        ("ibm",),
        "USD",
        "raw",
        (_bar(IBM, T1, 100), _bar(IBM, last, 110)),
        (gap,),
        (),
    )
    source = close_history(dataset)
    assert source.prices.index.is_monotonic_increasing
    assert pd.isna(
        indicator_table(source, momentum_window=1, volatility_window=2, periods_per_year=252).loc[
            "XNYS:IBM", "momentum"
        ]
    )


def test_quality_reasons_include_warned_observations_used_by_indicators():
    from market_research.research.indicators import close_history, indicator_table

    days = tuple(T1 + timedelta(days=offset) for offset in range(4))
    dataset = PriceDataset(
        days[-1],
        ("ibm",),
        "USD",
        "raw",
        (
            _bar(IBM, days[0], 100),
            _bar(IBM, days[1], 10, quality="warn", reasons=("large_close_jump",)),
            _bar(IBM, days[2], 100, quality="warn", reasons=("large_close_jump",)),
            _bar(IBM, days[3], 101),
        ),
        (),
        (),
    )
    row = indicator_table(
        close_history(dataset), momentum_window=2, volatility_window=2, periods_per_year=252
    ).loc["XNYS:IBM"]
    assert row["volatility_annualized"] > 0
    assert row["quality_reasons"] == ("large_close_jump",)


def test_annualization_basis_is_explicit_for_crypto():
    from market_research.research.indicators import IndicatorInput, indicator_table

    prices = pd.DataFrame(
        {"CRYPTO:BTC": [100, 110, 99, 109]},
        index=pd.date_range("2026-09-21", periods=4, freq="D", tz="UTC"),
    )
    source = IndicatorInput(prices, "point_in_time", "USD", "raw")
    result = indicator_table(source, momentum_window=2, volatility_window=2, periods_per_year=365)
    returns = prices.pct_change(fill_method=None)
    expected = returns.iloc[-2:, 0].std(ddof=1) * math.sqrt(365)
    assert result.loc["CRYPTO:BTC", "volatility_annualized"] == pytest.approx(expected)
    assert result.loc["CRYPTO:BTC", "periods_per_year"] == 365


def test_indicator_input_rejects_text_prices_and_invalid_annualization():
    from market_research.research.indicators import IndicatorInput, indicator_table

    index = pd.date_range("2026-09-21", periods=3, freq="D", tz="UTC")
    text_prices = IndicatorInput(
        pd.DataFrame({"XNYS:IBM": ["100", "101", "102"]}, index=index),
        "point_in_time",
        "USD",
        "raw",
    )
    with pytest.raises(ValueError, match="numeric"):
        indicator_table(text_prices, momentum_window=1, volatility_window=2, periods_per_year=252)
    numeric_prices = IndicatorInput(
        pd.DataFrame({"XNYS:IBM": [100, 101, 102]}, index=index),
        "point_in_time",
        "USD",
        "raw",
    )
    with pytest.raises(ValueError, match="periods_per_year"):
        indicator_table(numeric_prices, momentum_window=1, volatility_window=2, periods_per_year=0)


def test_indicator_input_requires_ordered_aware_positive_prices():
    from market_research.research.indicators import IndicatorInput, indicator_table

    for frame, word in (
        (
            pd.DataFrame({"XNYS:IBM": [100, 101]}, index=pd.date_range("2026-09-24", periods=2)),
            "timezone-aware",
        ),
        (
            pd.DataFrame(
                {"XNYS:IBM": [100, -1]},
                index=pd.date_range("2026-09-24", periods=2, tz="UTC"),
            ),
            "positive",
        ),
    ):
        with pytest.raises(ValueError, match=word):
            indicator_table(
                IndicatorInput(frame, "point_in_time", "USD", "raw"),
                momentum_window=1,
                volatility_window=2,
                periods_per_year=252,
            )
