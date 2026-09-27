"""Saved daily FX conversion never backdates later observations."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import Instrument, PriceBar, PriceGap
from market_research.prices import PriceExclusion
from market_research.research.dataset import PriceDataset, load_price_dataset
from market_research.storage import CacheKey, ResearchStore

DAYS = (date(2026, 9, 22), date(2026, 9, 23), date(2026, 9, 24))
AS_OF = datetime(2026, 9, 24, 23, tzinfo=UTC)
VALUATIONS = {day: datetime(day.year, day.month, day.day, 21, tzinfo=UTC) for day in DAYS}


def _bars(instrument: Instrument, symbol: str, closes: tuple[float, ...]) -> tuple[PriceBar, ...]:
    hour = 6 if instrument.market == "XTKS" else 18 if instrument.market == "FX" else 20
    return tuple(
        PriceBar(
            instrument=instrument,
            provider="yfinance",
            provider_symbol=symbol,
            interval="1d",
            bar_start=datetime(day.year, day.month, day.day, hour - 6, tzinfo=UTC),
            bar_end=datetime(day.year, day.month, day.day, hour, tzinfo=UTC),
            available_at=datetime(day.year, day.month, day.day, hour, 10, tzinfo=UTC),
            observed_at=datetime(day.year, day.month, day.day, hour, 20, tzinfo=UTC),
            close=close,
            adjustment="raw",
            revision_id="first",
        )
        for day, close in zip(DAYS, closes, strict=True)
    )


def _save(store: ResearchStore, instrument: Instrument, symbol: str, closes: tuple[float, ...]):
    snapshot = store.save(
        CacheKey("yfinance", "prices", instrument.instrument_id, "1d", instrument.currency, "raw"),
        f"saved {instrument.instrument_id}".encode(),
        observed_at=AS_OF,
        prices=_bars(instrument, symbol, closes),
    )
    return load_price_dataset(
        store,
        (snapshot.snapshot_id,),
        as_of=AS_OF,
        currency=instrument.currency,
        adjustment="raw",
    )


def _saved_inputs(root) -> tuple[tuple[PriceDataset, ...], PriceDataset]:
    with ResearchStore(root) as store:
        usd = _save(
            store, Instrument("XNYS", "XLE", "USD", "America/New_York"), "XLE", (100, 110, 105)
        )
        jpy = _save(
            store, Instrument("XTKS", "1329", "JPY", "Asia/Tokyo"), "1329.T", (1000, 1010, 1020)
        )
        fx = _save(store, Instrument("FX", "JPY=X", "JPY", "UTC"), "JPY=X", (150, 151, 152))
    return (usd, jpy), fx


def test_saved_usd_and_jpy_daily_prices_convert_at_explicit_valuation_times(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy
    from market_research.research.portfolio import virtual_risk_report

    prices, fx = _saved_inputs(tmp_path / "store")
    result = convert_price_datasets_to_jpy(prices, fx, VALUATIONS, max_fx_age=timedelta(hours=6))

    expected = pd.DataFrame(
        {"XNYS:XLE": [15000.0, 16610.0, 15960.0], "XTKS:1329": [1000.0, 1010.0, 1020.0]},
        index=pd.DatetimeIndex(VALUATIONS.values()),
    )
    pd.testing.assert_frame_equal(result.source.prices, expected)
    assert (result.source.currency, result.source.adjustment, result.source.mode) == (
        "JPY",
        "raw",
        "retrospective",
    )
    assert result.assumption == "retrospective_non_pit"
    assert result.price_snapshot_ids == (prices[0].snapshot_ids[0], prices[1].snapshot_ids[0])
    assert result.fx_snapshot_id == fx.snapshot_ids[0]
    assert tuple(use.rate for use in result.fx_uses) == (150.0, 151.0, 152.0)
    assert tuple(use.valuation_at for use in result.fx_uses) == tuple(VALUATIONS.values())
    assert all(
        use.provider == "yfinance" and use.provider_symbol == "JPY=X" for use in result.fx_uses
    )
    assert result.fx_uses[0].bar_end == datetime(2026, 9, 22, 18, tzinfo=UTC)
    assert result.fx_uses[0].available_at == datetime(2026, 9, 22, 18, 10, tzinfo=UTC)
    assert result.fx_uses[0].observed_at == datetime(2026, 9, 22, 18, 20, tzinfo=UTC)
    risk = virtual_risk_report(
        result.source,
        pd.Series({"XNYS:XLE": 0.5, "XTKS:1329": 0.5}),
        base_currency="JPY",
        lookback=2,
        periods_per_year=252,
    )
    assert risk.base_currency == "JPY"


def test_later_bulk_observation_cannot_be_backdated_to_a_price_valuation(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    usd = replace(
        prices[0],
        bars=(replace(prices[0].bars[0], observed_at=AS_OF), *prices[0].bars[1:]),
    )
    with pytest.raises(ValueError, match="price observed after valuation"):
        convert_price_datasets_to_jpy(
            (usd, prices[1]), fx, VALUATIONS, max_fx_age=timedelta(hours=6)
        )


@pytest.mark.parametrize("field", ["available_at", "observed_at"])
def test_later_fx_observation_is_not_used_at_earlier_valuation(tmp_path, field):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    delayed = replace(
        fx,
        bars=(
            fx.bars[0],
            replace(fx.bars[1], **{field: VALUATIONS[DAYS[1]] + timedelta(minutes=10)}),
            fx.bars[2],
        ),
    )
    result = convert_price_datasets_to_jpy(
        prices, delayed, VALUATIONS, max_fx_age=timedelta(hours=30)
    )
    assert result.fx_uses[1].rate == 150.0
    assert result.source.prices.loc[VALUATIONS[DAYS[1]], "XNYS:XLE"] == 16500.0


def test_price_bar_end_alone_does_not_make_a_close_available(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    too_early = {**VALUATIONS, DAYS[0]: datetime(2026, 9, 22, 20, 5, tzinfo=UTC)}
    with pytest.raises(ValueError, match="price observed after valuation"):
        convert_price_datasets_to_jpy(prices, fx, too_early, max_fx_age=timedelta(hours=6))


def test_stale_or_missing_fx_fails_explicitly(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    with pytest.raises(ValueError, match="FX is stale"):
        convert_price_datasets_to_jpy(prices, fx, VALUATIONS, max_fx_age=timedelta(hours=2))
    with pytest.raises(ValueError, match="FX prices are missing"):
        convert_price_datasets_to_jpy(
            prices, replace(fx, bars=()), VALUATIONS, max_fx_age=timedelta(hours=6)
        )


def test_rejected_quality_or_mixed_adjustment_fails(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    rejected_price = replace(
        prices[0], bars=(replace(prices[0].bars[0], quality="reject"), *prices[0].bars[1:])
    )
    rejected_fx = replace(fx, bars=(replace(fx.bars[0], quality="reject"), *fx.bars[1:]))
    mixed_adjustment = replace(
        prices[0], bars=(replace(prices[0].bars[0], adjustment="split"), *prices[0].bars[1:])
    )
    with pytest.raises(ValueError, match="quality"):
        convert_price_datasets_to_jpy(
            (rejected_price, prices[1]), fx, VALUATIONS, max_fx_age=timedelta(hours=6)
        )
    with pytest.raises(ValueError, match="quality"):
        convert_price_datasets_to_jpy(
            prices, rejected_fx, VALUATIONS, max_fx_age=timedelta(hours=6)
        )
    with pytest.raises(ValueError, match="raw daily"):
        convert_price_datasets_to_jpy(
            (mixed_adjustment, prices[1]), fx, VALUATIONS, max_fx_age=timedelta(hours=6)
        )


def test_missing_asset_session_does_not_forward_fill(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    missing = replace(prices[1], bars=(prices[1].bars[0], prices[1].bars[2]))
    with pytest.raises(ValueError, match="missing price"):
        convert_price_datasets_to_jpy(
            (prices[0], missing), fx, VALUATIONS, max_fx_age=timedelta(hours=6)
        )


def test_fx_gap_cannot_be_silently_filled_from_previous_day(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    gap = PriceGap(
        instrument=fx.bars[1].instrument,
        provider="yfinance",
        provider_symbol="JPY=X",
        interval="1d",
        session_date=DAYS[1],
        available_at=VALUATIONS[DAYS[1]] - timedelta(minutes=30),
        observed_at=VALUATIONS[DAYS[1]] - timedelta(minutes=20),
        adjustment="raw",
        reason="no_trade",
    )
    missing = replace(fx, bars=(fx.bars[0], fx.bars[2]), gaps=(gap,))
    with pytest.raises(ValueError, match="FX gap"):
        convert_price_datasets_to_jpy(prices, missing, VALUATIONS, max_fx_age=timedelta(hours=30))


def test_provider_switch_for_one_asset_is_rejected(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    first = replace(prices[0], bars=prices[0].bars[:2])
    second = replace(
        prices[0],
        snapshot_ids=("other-saved-snapshot",),
        bars=(replace(prices[0].bars[2], provider="another"),),
    )
    with pytest.raises(ValueError, match="provider"):
        convert_price_datasets_to_jpy(
            (first, second, prices[1]), fx, VALUATIONS, max_fx_age=timedelta(hours=6)
        )


def test_newer_unfinished_fx_bar_cannot_hide_behind_prior_rate(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    unfinished = replace(fx.bars[1], is_final=False)
    altered = replace(
        fx,
        bars=(fx.bars[0], fx.bars[2]),
        exclusions=(PriceExclusion(unfinished, "non_final"),),
    )
    with pytest.raises(ValueError, match="FX non_final"):
        convert_price_datasets_to_jpy(prices, altered, VALUATIONS, max_fx_age=timedelta(hours=30))


def test_newer_unfinished_price_bar_is_not_ignored(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    bar = prices[0].bars[1]
    unfinished = replace(bar, is_final=False, bar_end=bar.bar_end + timedelta(minutes=30))
    altered = replace(prices[0], exclusions=(PriceExclusion(unfinished, "non_final"),))
    with pytest.raises(ValueError, match="price non_final"):
        convert_price_datasets_to_jpy(
            (altered, prices[1]), fx, VALUATIONS, max_fx_age=timedelta(hours=6)
        )


def test_missing_price_session_cannot_be_hidden_by_omitting_valuation(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    omitted = {day: when for day, when in VALUATIONS.items() if day != DAYS[1]}
    usd = replace(prices[0], bars=(prices[0].bars[0], prices[0].bars[2]))
    gap = PriceGap(
        instrument=prices[1].bars[1].instrument,
        provider="yfinance",
        provider_symbol="1329.T",
        interval="1d",
        session_date=DAYS[1],
        available_at=VALUATIONS[DAYS[1]] - timedelta(minutes=30),
        observed_at=VALUATIONS[DAYS[1]] - timedelta(minutes=20),
        adjustment="raw",
    )
    jpy = replace(prices[1], bars=(prices[1].bars[0], prices[1].bars[2]), gaps=(gap,))
    with pytest.raises(ValueError, match="price gap"):
        convert_price_datasets_to_jpy((usd, jpy), fx, omitted, max_fx_age=timedelta(hours=6))


def test_jpy_equity_cannot_masquerade_as_jpy_equals_x_fx(tmp_path):
    from market_research.research.fx_conversion import convert_price_datasets_to_jpy

    prices, fx = _saved_inputs(tmp_path / "store")
    equity = Instrument("XTKS", "1329", "JPY", "Asia/Tokyo")
    mislabeled = replace(fx, bars=tuple(replace(bar, instrument=equity) for bar in fx.bars))
    with pytest.raises(ValueError, match="FX instrument"):
        convert_price_datasets_to_jpy(prices, mislabeled, VALUATIONS, max_fx_age=timedelta(hours=6))
