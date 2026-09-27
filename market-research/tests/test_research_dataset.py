"""Offline research inputs retain snapshot provenance and price finality."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from market_research.contracts import Instrument, PriceBar, PriceGap
from market_research.storage import CacheKey, ResearchStore

AS_OF = datetime(2026, 9, 25, 22, tzinfo=UTC)


def _bar(instrument: Instrument) -> PriceBar:
    return PriceBar(
        instrument=instrument,
        provider="yfinance",
        interval="1d",
        bar_start=AS_OF - timedelta(days=1, hours=7),
        bar_end=AS_OF - timedelta(days=1),
        available_at=AS_OF - timedelta(hours=1),
        observed_at=AS_OF,
        close=100.0,
        adjustment="raw",
        revision_id="first",
    )


def _save(store: ResearchStore, instrument: Instrument):
    key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", "USD", "raw")
    return store.save(
        key, instrument.symbol.encode(), observed_at=AS_OF, prices=(_bar(instrument),)
    )


def test_loads_explicit_complete_snapshots_without_losing_provenance(tmp_path):
    from market_research.research.dataset import load_price_dataset

    instruments = (
        Instrument("XNYS", "IBM", "USD", "America/New_York"),
        Instrument("XNAS", "MSFT", "USD", "America/New_York"),
    )
    with ResearchStore(tmp_path) as store:
        ids = tuple(_save(store, instrument).snapshot_id for instrument in instruments)
        result = load_price_dataset(
            store,
            ids,
            as_of=AS_OF.astimezone(ZoneInfo("Asia/Tokyo")),
            currency="USD",
            adjustment="raw",
        )
    assert result.mode == "retrospective"
    assert result.as_of.tzinfo is UTC
    assert result.snapshot_ids == ids
    assert {bar.instrument.instrument_id for bar in result.bars} == {"XNYS:IBM", "XNAS:MSFT"}
    assert result.currency == "USD"
    assert result.adjustment == "raw"
    assert result.gaps == ()
    assert result.exclusions == ()


def test_empty_or_duplicate_snapshot_selection_is_rejected(tmp_path):
    from market_research.research.dataset import load_price_dataset

    with ResearchStore(tmp_path) as store:
        with pytest.raises(ValueError, match="snapshot"):
            load_price_dataset(store, (), as_of=AS_OF, currency="USD", adjustment="raw")
        saved = _save(store, Instrument("XNYS", "IBM", "USD", "America/New_York"))
        with pytest.raises(ValueError, match="duplicate"):
            load_price_dataset(
                store,
                (saved.snapshot_id, saved.snapshot_id),
                as_of=AS_OF,
                currency="USD",
                adjustment="raw",
            )


def test_two_snapshots_for_one_instrument_are_rejected(tmp_path):
    from market_research.research.dataset import load_price_dataset

    instrument = Instrument("XNYS", "IBM", "USD", "America/New_York")
    key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", "USD", "raw")
    with ResearchStore(tmp_path) as store:
        first = _save(store, instrument)
        later = AS_OF + timedelta(minutes=1)
        second = store.save(
            key,
            b"second",
            observed_at=later,
            prices=(
                replace(
                    _bar(instrument),
                    observed_at=later,
                    available_at=later,
                    revision_id="second",
                ),
            ),
        )
        with pytest.raises(ValueError, match="duplicate instrument"):
            load_price_dataset(
                store,
                (first.snapshot_id, second.snapshot_id),
                as_of=later,
                currency="USD",
                adjustment="raw",
            )


def test_future_or_partial_snapshot_cannot_supply_research_prices(tmp_path):
    from market_research.research.dataset import load_price_dataset

    instrument = Instrument("XNYS", "IBM", "USD", "America/New_York")
    key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", "USD", "raw")
    with ResearchStore(tmp_path) as store:
        future_at = AS_OF + timedelta(days=1)
        future = store.save(
            key,
            b"future",
            observed_at=future_at,
            prices=(
                replace(
                    _bar(instrument),
                    observed_at=future_at,
                    available_at=future_at,
                    revision_id="future",
                ),
            ),
        )
        partial = store.save(
            key,
            b"partial",
            observed_at=AS_OF,
            prices=(_bar(instrument),),
            complete=False,
            cursor="next",
        )
        with pytest.raises(ValueError, match="future"):
            load_price_dataset(
                store, (future.snapshot_id,), as_of=AS_OF, currency="USD", adjustment="raw"
            )
        with pytest.raises(ValueError, match="complete"):
            load_price_dataset(
                store, (partial.snapshot_id,), as_of=AS_OF, currency="USD", adjustment="raw"
            )
        with pytest.raises(ValueError, match="timezone-aware"):
            load_price_dataset(
                store,
                (partial.snapshot_id,),
                as_of=AS_OF.replace(tzinfo=None),
                currency="USD",
                adjustment="raw",
            )


def test_currency_adjustment_and_provider_mixing_are_rejected(tmp_path):
    from market_research.research.dataset import load_price_dataset

    instrument = Instrument("XNYS", "IBM", "USD", "America/New_York")
    with ResearchStore(tmp_path) as store:
        saved = _save(store, instrument)
        for currency, adjustment, word in (
            ("JPY", "raw", "currency"),
            ("USD", "unknown", "adjustment"),
        ):
            with pytest.raises(ValueError, match=word):
                load_price_dataset(
                    store,
                    (saved.snapshot_id,),
                    as_of=AS_OF,
                    currency=currency,
                    adjustment=adjustment,
                )
        alternate = store.save(
            CacheKey("stooq", "prices", instrument.instrument_id, "1d", "USD", "raw"),
            b"stooq",
            observed_at=AS_OF,
            prices=(replace(_bar(instrument), provider="stooq", revision_id="stooq"),),
        )
        with pytest.raises(ValueError, match="provider"):
            load_price_dataset(
                store,
                (saved.snapshot_id, alternate.snapshot_id),
                as_of=AS_OF,
                currency="USD",
                adjustment="raw",
            )


def test_nonfinal_bar_and_gap_remain_auditable_but_not_final_prices(tmp_path):
    from market_research.research.dataset import load_price_dataset

    instrument = Instrument("XNYS", "IBM", "USD", "America/New_York")
    partial = replace(
        _bar(instrument),
        bar_start=AS_OF - timedelta(hours=1),
        bar_end=AS_OF + timedelta(hours=1),
        available_at=AS_OF,
        is_final=False,
        revision_id="intraday",
    )
    gap = PriceGap(
        instrument,
        "yfinance",
        "IBM",
        "1d",
        AS_OF.date(),
        AS_OF,
        AS_OF,
        "raw",
    )
    with ResearchStore(tmp_path) as store:
        key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", "USD", "raw")
        saved = store.save(
            key, b"partial-and-gap", observed_at=AS_OF, prices=(partial,), gaps=(gap,)
        )
        result = load_price_dataset(
            store, (saved.snapshot_id,), as_of=AS_OF, currency="USD", adjustment="raw"
        )
    assert result.bars == ()
    assert result.gaps == (gap,)
    assert tuple(row.reason for row in result.exclusions) == ("non_final",)
