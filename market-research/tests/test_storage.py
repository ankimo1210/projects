from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.contracts import Instrument, MacroObservation, PriceBar
from market_research.storage import CacheKey, CacheUnavailableError, ResearchStore

T1 = datetime(2026, 9, 25, 7, tzinfo=UTC)
T2 = T1 + timedelta(days=1)
INST = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
KEY = CacheKey("yfinance", "prices", INST.instrument_id, "1d", "JPY", "raw")


def bar(**changes):
    row = PriceBar(
        INST,
        "yfinance",
        "1d",
        T1 - timedelta(hours=7),
        T1 - timedelta(minutes=30),
        T1,
        T1,
        100.0,
        "raw",
        "v1",
        provider_symbol="7203.T",
    )
    return replace(row, **changes)


def test_snapshots_are_immutable_idempotent_and_survive_reopen(tmp_path):
    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, prices=(bar(),))
        assert store.save(KEY, b"first", observed_at=T1, prices=(bar(),)) == first
        changed = bar(close=101, revision_id="v2", available_at=T2, observed_at=T2)
        second = store.save(KEY, b"second", observed_at=T2, prices=(changed,))
        assert first.raw_hash != second.raw_hash
        assert store.read_raw(first) == b"first"
    with ResearchStore(tmp_path) as store:
        assert store.price_view(INST.instrument_id, "yfinance", T1, "raw").bars == (bar(),)
        assert store.price_view(INST.instrument_id, "yfinance", T2, "raw").bars == (changed,)


def test_same_symbol_provider_currency_and_adjustment_have_distinct_keys():
    assert (
        len(
            {
                KEY.digest,
                replace(KEY, provider="stooq").digest,
                replace(KEY, currency="USD").digest,
                replace(KEY, adjustment="unknown").digest,
                replace(KEY, identity="XNYS:7203").digest,
            }
        )
        == 5
    )


def test_provider_series_do_not_overwrite_each_other(tmp_path):
    with ResearchStore(tmp_path) as store:
        store.save(KEY, b"y", observed_at=T1, prices=(bar(),))
        other = bar(provider="stooq", adjustment="unknown", close=99)
        store.save(
            replace(KEY, provider="stooq", adjustment="unknown"),
            b"s",
            observed_at=T1,
            prices=(other,),
        )
        assert store.price_view(INST.instrument_id, "yfinance", T1, "raw").bars[0].close == 100
        assert store.price_view(INST.instrument_id, "stooq", T1, "unknown").bars[0].close == 99


def test_currency_series_survive_together_and_require_explicit_selection(tmp_path):
    dollar = bar(instrument=replace(INST, currency="USD"), close=0.7)
    with ResearchStore(tmp_path) as store:
        yen_snapshot = store.save(KEY, b"yen", observed_at=T1, prices=(bar(),))
        usd_snapshot = store.save(
            replace(KEY, currency="USD"), b"usd", observed_at=T1, prices=(dollar,)
        )
        assert store.snapshot_price_view(usd_snapshot, T1).bars == (dollar,)
        assert store.snapshot_price_view(yen_snapshot, T1).bars == (bar(),)
        with pytest.raises(ValueError, match="currency"):
            store.price_view(INST.instrument_id, "yfinance", T1, "raw")
        assert store.price_view(INST.instrument_id, "yfinance", T1, "raw", currency="USD").bars == (
            dollar,
        )


def test_conflict_rolls_back_entire_batch(tmp_path):
    with ResearchStore(tmp_path) as store:
        store.save(KEY, b"first", observed_at=T1, prices=(bar(),))
        valid = bar(revision_id="v2", available_at=T2, observed_at=T2, close=102)
        with pytest.raises(ValueError, match="conflicting"):
            store.save(KEY, b"bad", observed_at=T2, prices=(valid, bar(close=999)))
        assert store.price_view(INST.instrument_id, "yfinance", T2, "raw").bars == (bar(),)
        assert store.latest_snapshot(KEY, now=T2, max_age=timedelta(days=2)).observed_at == T1


def test_incomplete_batch_is_retained_but_not_queryable(tmp_path):
    with ResearchStore(tmp_path) as store:
        partial = store.save(
            KEY, b"partial", observed_at=T1, prices=(bar(),), complete=False, cursor="page-2"
        )
        assert store.read_raw(partial) == b"partial"
        with pytest.raises(CacheUnavailableError):
            store.latest_snapshot(KEY, now=T1, max_age=timedelta(days=1))
        with pytest.raises(ValueError, match="unavailable"):
            store.price_view(INST.instrument_id, "yfinance", T1, "raw")
        assert store.pending_snapshot(KEY).cursor == "page-2"


def test_stale_and_future_snapshots_are_never_silent(tmp_path):
    with ResearchStore(tmp_path) as store:
        store.save(KEY, b"first", observed_at=T1, prices=(bar(),))
        with pytest.raises(CacheUnavailableError, match="stale"):
            store.latest_snapshot(KEY, now=T2, max_age=timedelta(hours=1))
        stale = store.latest_snapshot(KEY, now=T2, max_age=timedelta(hours=1), allow_stale=True)
        assert stale.stale
        with pytest.raises(CacheUnavailableError):
            store.latest_snapshot(KEY, now=T1 - timedelta(seconds=1), max_age=timedelta(days=1))


def test_raw_hash_corruption_is_detected(tmp_path):
    with ResearchStore(tmp_path) as store:
        saved = store.save(KEY, b"first", observed_at=T1, prices=(bar(),))
        saved.raw_path.write_bytes(b"corrupt")
        with pytest.raises(ValueError, match="hash"):
            store.read_raw(saved)
        with pytest.raises(ValueError, match="hash"):
            store.save(KEY, b"first", observed_at=T1, prices=(bar(),))


def test_macro_vintages_are_read_at_release_boundary(tmp_path):
    key = CacheKey("official", "macro", "CPI", "monthly", "index", "none")
    first = MacroObservation("CPI", date(2026, 8, 1), T1, 100, "official", "first")
    second = replace(first, release_at=T2, value=101, vintage_id="revision")
    with ResearchStore(tmp_path) as store:
        store.save(key, b"vintages", observed_at=T2, macro=(first, second))
        assert store.macro_view("CPI", T1 - timedelta(seconds=1), "official") == ()
        assert store.macro_view("CPI", T1, "official") == (first,)
        assert store.macro_view("CPI", T2, "official") == (second,)


def test_reject_naive_snapshot_and_mismatched_identity(tmp_path):
    with ResearchStore(tmp_path) as store:
        with pytest.raises(ValueError, match="timezone-aware"):
            store.save(KEY, b"x", observed_at=T1.replace(tzinfo=None))
        with pytest.raises(ValueError, match="cache key"):
            store.save(replace(KEY, currency="USD"), b"x", observed_at=T1, prices=(bar(),))


def test_partial_price_observation_is_audited_after_storage(tmp_path):
    row = bar(
        is_final=False, available_at=T1 - timedelta(hours=1), observed_at=T1 - timedelta(hours=1)
    )
    with ResearchStore(tmp_path) as store:
        store.save(KEY, b"partial-bar", observed_at=row.observed_at, prices=(row,))
        view = store.price_view(INST.instrument_id, "yfinance", T2, "raw")
        assert view.bars == ()
        assert view.exclusions[0].bar == row
