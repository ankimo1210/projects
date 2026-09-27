"""Saved SEC facts remain tied to the requested filing and observation time."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import FundamentalObservation
from market_research.storage import CacheKey, ResearchStore

T1 = datetime(2026, 9, 25, 12, tzinfo=UTC)
T2 = T1 + timedelta(days=1)
CIK = 320193
IDENTITY = "CIK0000320193:us-gaap:Assets:USD:10-K"
KEY = CacheKey("sec", "fundamental", IDENTITY, "annual", "USD", "none")


def _fact(period_end: date, value: float, *, available_at: datetime = T1):
    return FundamentalObservation(
        CIK,
        "us-gaap",
        "Assets",
        "USD",
        None,
        period_end,
        date(2026, 9, 24),
        available_at,
        None,
        value,
        "10-K",
        f"accession-{period_end.isoformat()}-{value}",
    )


def _request(snapshot_id: str | None, *, asset: str = "XNAS:AAPL"):
    from market_research.research.fundamentals import FundamentalField, FundamentalRequest

    return FundamentalRequest(
        asset,
        CIK,
        FundamentalField("assets", "us-gaap", "Assets", "USD", "10-K"),
        snapshot_id,
    )


def test_latest_filing_and_uncollected_field_keep_provenance(tmp_path):
    from market_research.research.fundamentals import load_fundamental_table

    with ResearchStore(tmp_path) as store:
        saved = store.save(
            KEY,
            b"companyfacts",
            observed_at=T1,
            fundamentals=(
                _fact(date(2024, 9, 28), 80),
                _fact(date(2025, 9, 27), 100),
            ),
        )
        result = load_fundamental_table(
            store,
            (_request(saved.snapshot_id), _request(None, asset="XNAS:MSFT")),
            as_of=T1,
        )
    row = result.loc[("XNAS:AAPL", "assets")]
    assert row["value"] == 100
    assert row["unit"] == "USD"
    assert row["period_end"] == date(2025, 9, 27)
    assert row["available_at"] == T1
    assert row["observed_at"] == T1
    assert row["vintage_kind"] == "estimated"
    assert row["snapshot_id"] == saved.snapshot_id
    assert row["as_of"] == T1
    assert row["missing_reason"] == ""
    missing = result.loc[("XNAS:MSFT", "assets")]
    assert pd.isna(missing["value"])
    assert missing["missing_reason"] == "not_collected"


def test_future_snapshot_and_unavailable_filing_are_not_used(tmp_path):
    from market_research.research.fundamentals import load_fundamental_table

    with ResearchStore(tmp_path) as store:
        future_snapshot = store.save(
            KEY, b"future", observed_at=T2, fundamentals=(_fact(date(2025, 9, 27), 100),)
        )
        with pytest.raises(ValueError, match="future snapshot"):
            load_fundamental_table(store, (_request(future_snapshot.snapshot_id),), as_of=T1)
        not_released = store.save(
            KEY,
            b"not-released",
            observed_at=T1,
            fundamentals=(_fact(date(2025, 9, 27), 100, available_at=T2),),
        )
        result = load_fundamental_table(store, (_request(not_released.snapshot_id),), as_of=T1)
    row = result.loc[("XNAS:AAPL", "assets")]
    assert pd.isna(row["value"])
    assert row["missing_reason"] == "not_available"


def test_wrong_identity_partial_snapshot_and_naive_time_fail_closed(tmp_path):
    from market_research.research.fundamentals import load_fundamental_table

    with ResearchStore(tmp_path) as store:
        saved = store.save(
            KEY, b"ok", observed_at=T1, fundamentals=(_fact(date(2025, 9, 27), 100),)
        )
        partial = store.save(
            KEY,
            b"partial",
            observed_at=T1,
            fundamentals=(_fact(date(2025, 9, 27), 100),),
            complete=False,
            cursor="more",
        )
        with pytest.raises(ValueError, match="identity"):
            load_fundamental_table(
                store, (replace(_request(saved.snapshot_id), cik=999999),), as_of=T1
            )
        with pytest.raises(ValueError, match="complete"):
            load_fundamental_table(store, (_request(partial.snapshot_id),), as_of=T1)
        with pytest.raises(ValueError, match="timezone-aware"):
            load_fundamental_table(
                store, (_request(saved.snapshot_id),), as_of=T1.replace(tzinfo=None)
            )


def test_same_period_end_with_two_period_starts_is_ambiguous(tmp_path):
    from market_research.research.fundamentals import load_fundamental_table

    annual = _fact(date(2025, 9, 27), 100)
    quarterly = replace(annual, period_start=date(2025, 6, 29), value=25, accession="other-period")
    with ResearchStore(tmp_path) as store:
        saved = store.save(KEY, b"ambiguous", observed_at=T1, fundamentals=(annual, quarterly))
        with pytest.raises(ValueError, match="ambiguous"):
            load_fundamental_table(store, (_request(saved.snapshot_id),), as_of=T1)


def test_later_filing_revision_does_not_change_earlier_snapshot(tmp_path):
    from market_research.research.fundamentals import load_fundamental_table

    period_end = date(2025, 9, 27)
    original = _fact(period_end, 100)
    revised = replace(
        original,
        value=120,
        available_at=T2,
        accession="amendment",
    )
    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, fundamentals=(original,))
        second = store.save(KEY, b"revised", observed_at=T2, fundamentals=(original, revised))
        before = load_fundamental_table(store, (_request(first.snapshot_id),), as_of=T1)
        after = load_fundamental_table(store, (_request(second.snapshot_id),), as_of=T2)
    assert before.loc[("XNAS:AAPL", "assets"), "value"] == 100
    assert after.loc[("XNAS:AAPL", "assets"), "value"] == 120
