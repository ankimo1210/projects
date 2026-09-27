from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.contracts import FundamentalObservation, MacroObservation
from market_research.storage import CacheKey, CacheUnavailableError, ResearchStore

T1 = datetime(2026, 9, 25, 12, tzinfo=UTC)
T2 = T1 + timedelta(days=1)
MACRO_KEY = CacheKey("alfred", "macro", "GDP", "quarterly", "billions", "none")
FUND_KEY = CacheKey(
    "sec", "fundamental", "CIK0000320193:us-gaap:Assets:USD:10-K", "annual", "USD", "none"
)


def fundamental(**changes):
    row = FundamentalObservation(
        cik=320193,
        taxonomy="us-gaap",
        concept="Assets",
        unit="USD",
        period_start=None,
        period_end=date(2025, 9, 27),
        filed=date(2025, 10, 31),
        available_at=T1,
        observed_at=T2,
        value=100.0,
        form="10-K",
        accession="0000320193-25-000001",
    )
    return replace(row, **changes)


def test_macro_metadata_survives_store_and_release_boundary(tmp_path):
    row = MacroObservation(
        "GDP",
        date(2025, 1, 1),
        T1,
        100,
        "alfred",
        "2025-04-01",
        vintage_kind="estimated",
        unit="billions",
        frequency="quarterly",
        seasonal_adjustment="sa",
        release_precision="date",
        source_release_date=date(2025, 4, 1),
        observed_at=T2,
        source_ref="GDP",
    )
    with ResearchStore(tmp_path) as store:
        store.save(MACRO_KEY, b"source", observed_at=T2, macro=(row,))
        assert store.macro_view("GDP", T1 - timedelta(microseconds=1), "alfred") == ()
        assert store.macro_view("GDP", T1, "alfred") == (row,)


def test_fundamental_revision_is_visible_only_after_filing_boundary(tmp_path):
    original = fundamental()
    revision = fundamental(
        accession="0000320193-25-000002",
        available_at=T2,
        observed_at=T2,
        value=101.0,
    )
    with ResearchStore(tmp_path) as store:
        store.save(FUND_KEY, b"first", observed_at=T2, fundamentals=(original, revision))
        query = (320193, "us-gaap", "Assets", "USD", "10-K")
        assert store.fundamental_view(*query, T1 - timedelta(microseconds=1)) == ()
        assert store.fundamental_view(*query, T1) == (original,)
        assert store.fundamental_view(*query, T2) == (revision,)


def test_partial_fundamentals_do_not_publish_and_conflict_rolls_back(tmp_path):
    first = fundamental()
    with ResearchStore(tmp_path) as store:
        store.save(
            FUND_KEY,
            b"pending",
            observed_at=T2,
            fundamentals=(first,),
            complete=False,
            cursor="next",
        )
        assert store.fundamental_view(320193, "us-gaap", "Assets", "USD", "10-K", T2) == ()
        with pytest.raises(CacheUnavailableError):
            store.latest_snapshot(FUND_KEY, now=T2, max_age=timedelta(days=1))
        store.save(FUND_KEY, b"first", observed_at=T2, fundamentals=(first,))
        second = fundamental(accession="0000320193-25-000003", available_at=T2, value=102.0)
        with pytest.raises(ValueError, match="conflicting"):
            store.save(
                FUND_KEY, b"bad", observed_at=T2, fundamentals=(second, replace(first, value=999))
            )
        assert store.fundamental_view(320193, "us-gaap", "Assets", "USD", "10-K", T2) == (first,)


def test_fundamental_rejects_naive_time_and_wrong_unit(tmp_path):
    with pytest.raises(ValueError, match="timezone-aware"):
        fundamental(available_at=T1.replace(tzinfo=None))
    with ResearchStore(tmp_path) as store, pytest.raises(ValueError, match="cache key"):
        store.save(FUND_KEY, b"bad", observed_at=T2, fundamentals=(fundamental(unit="shares"),))


def test_snapshot_views_never_mix_other_requests_or_partial_rows(tmp_path):
    first = MacroObservation("GDP", date(2025, 1, 1), T1, 100, "alfred", "first")
    other = replace(first, value=200, source="esri_gdp", vintage_id="other")
    with ResearchStore(tmp_path) as store:
        a = store.save(MACRO_KEY, b"a", observed_at=T2, macro=(first,))
        b_key = replace(MACRO_KEY, provider="esri_gdp")
        store.save(b_key, b"b", observed_at=T2, macro=(other,))
        partial = store.save(
            MACRO_KEY,
            b"partial",
            observed_at=T2,
            macro=(replace(first, vintage_id="partial", release_at=T2),),
            complete=False,
            cursor="2",
        )
        assert store.snapshot_macro_view(a, T1) == (first,)
        with pytest.raises(CacheUnavailableError):
            store.snapshot_macro_view(partial, T2)
        f = store.save(FUND_KEY, b"filing", observed_at=T2, fundamentals=(fundamental(),))
        assert store.snapshot_fundamental_view(f, T1) == (fundamental(),)
        with pytest.raises(CacheUnavailableError):
            store.snapshot_fundamental_view(a, T2)
