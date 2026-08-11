from __future__ import annotations

from datetime import UTC, date, datetime, timezone

import numpy as np
import pytest
from quant_textbook.sec_pit import (
    FilingRecord,
    PITUniverseSpec,
    UnresolvedAccessionError,
    audit_split_counts,
    build_filing_index,
    fundamentals_error_metrics,
    next_us_business_day,
    normalize_accession,
    resolve_first_reported_vintages,
    select_fixed_anchor_cohort,
)


def _table(*rows: tuple[str, str, str, str, str]) -> dict[str, list[str]]:
    return {
        "accessionNumber": [row[0] for row in rows],
        "filingDate": [row[1] for row in rows],
        "acceptanceDateTime": [row[2] for row in rows],
        "form": [row[3] for row in rows],
        "cik": [row[4] for row in rows],
    }


def test_accession_normalization_and_calendar_are_explicit() -> None:
    assert normalize_accession("0000320193-25-000079") == "0000320193-25-000079"
    assert normalize_accession("000032019325000079") == "0000320193-25-000079"
    assert next_us_business_day("2025-07-03") == date(2025, 7, 7)
    assert next_us_business_day(datetime(2025, 1, 1, tzinfo=UTC)) == date(2025, 1, 2)


def test_filing_index_requires_acceptance_and_merges_historical_archive() -> None:
    recent = _table(
        ("0000320193-25-000079", "2025-02-01", "2025-02-01T18:00:00-05:00", "10-Q", "320193"),
    )
    archive = _table(
        ("0000320193-14-000010", "2014-02-01", "2014-02-01T17:00:00-05:00", "10-K", "320193"),
    )
    index = build_filing_index(recent, [archive])
    assert sorted(index) == ["0000320193-14-000010", "0000320193-25-000079"]
    assert index["0000320193-14-000010"].availability_date() == date(2014, 2, 3)

    missing_acceptance = dict(recent)
    missing_acceptance["acceptanceDateTime"] = [None]
    with pytest.raises(ValueError, match="acceptanceDateTime"):
        build_filing_index(missing_acceptance)


def test_first_reported_vintage_uses_archive_and_rejects_unresolved_accession() -> None:
    filing_index = build_filing_index(
        _table(
            ("0000320193-25-000079", "2025-02-01", "2025-02-01T18:00:00-05:00", "10-Q", "320193"),
            ("0000320193-26-000079", "2026-02-01", "2026-02-01T18:00:00-05:00", "10-Q/A", "320193"),
        )
    )
    facts = [
        {
            "cik": 320193,
            "concept": "us-gaap/Assets",
            "unit": "USD",
            "start": None,
            "end": "2024-12-31",
            "val": 100_000_000,
            "accn": "0000320193-25-000079",
        },
        {
            "cik": 320193,
            "concept": "us-gaap/Assets",
            "unit": "USD",
            "start": None,
            "end": "2024-12-31",
            "val": 110_000_000,
            "accn": "0000320193-26-000079",
        },
    ]
    vintages = resolve_first_reported_vintages(facts, filing_index)
    assert len(vintages) == 1
    assert vintages[0]["value"] == 100_000_000
    assert vintages[0]["availability_date"] == "2025-02-03"

    with pytest.raises(UnresolvedAccessionError, match=r"filings\.files"):
        resolve_first_reported_vintages(
            [
                {
                    **facts[0],
                    "accn": "0000320193-24-000001",
                }
            ],
            filing_index,
        )


def test_first_reported_vintage_orders_by_availability_not_filing_date() -> None:
    filing_index = build_filing_index(
        _table(
            ("0000320193-25-000001", "2025-01-01", "2025-01-10T16:00:00-05:00", "10-Q", "320193"),
            ("0000320193-25-000002", "2025-01-02", "2025-01-02T16:00:00-05:00", "10-Q", "320193"),
        )
    )
    facts = [
        {
            "cik": 320193,
            "concept": "us-gaap/Assets",
            "unit": "USD",
            "start": None,
            "end": "2024-12-31",
            "val": 100_000_000,
            "accn": "0000320193-25-000001",
        },
        {
            "cik": 320193,
            "concept": "us-gaap/Assets",
            "unit": "USD",
            "start": None,
            "end": "2024-12-31",
            "val": 110_000_000,
            "accn": "0000320193-25-000002",
        },
    ]

    vintage = resolve_first_reported_vintages(facts, filing_index)[0]

    assert vintage["accn"] == "0000320193-25-000002"
    assert vintage["value"] == 110_000_000
    assert vintage["availability_date"] == "2025-01-03"


def test_fixed_anchor_cohort_excludes_future_selected_and_small_assets() -> None:
    spec = PITUniverseSpec(
        anchor_period_end=date(2015, 12, 31),
        anchor_as_of=date(2016, 4, 1),
        analysis_start=date(2016, 4, 1),
    )
    vintages = [
        {
            "cik": 1,
            "concept": "us-gaap/Assets",
            "unit": "USD",
            "end": "2015-12-31",
            "value": 200_000_000,
            "availability_date": "2016-03-01",
        },
        {
            "cik": 2,
            "concept": "us-gaap/Assets",
            "unit": "USD",
            "end": "2015-12-31",
            "value": 200_000_000,
            "availability_date": "2016-04-02",
        },
        {
            "cik": 3,
            "concept": "us-gaap/Assets",
            "unit": "USD",
            "end": "2015-12-31",
            "value": 50_000_000,
            "availability_date": "2016-03-01",
        },
    ]
    selection = select_fixed_anchor_cohort(vintages, spec)
    assert selection.eligible_ciks == (1,)
    assert selection.candidate_rows == 1
    assert selection.selected_rows == 1


def test_split_gate_and_fundamentals_metrics_are_locked() -> None:
    rows = [
        {"cik": index, "target_avail": "2023-01-01" if index % 2 else "2022-12-31"}
        for index in range(1, 7)
    ]
    audit = audit_split_counts(
        rows,
        time_cutoff=date(2023, 1, 1),
        company_modulus=3,
        company_remainder=0,
        minimum_required=2,
    )
    assert audit.total_rows == 6
    assert audit.time_holdout_rows == 3
    assert audit.company_holdout_rows == 2
    assert audit.both_holdout_rows == 1
    assert not audit.accepted

    metrics = fundamentals_error_metrics(np.array([1.0, 2.0, 5.0]), [1.5, 1.0, 4.0])
    assert metrics.n == 3
    assert metrics.mae == pytest.approx(5.0 / 6.0)
    assert metrics.median_absolute_error == pytest.approx(1.0)
    assert metrics.rmse == pytest.approx(np.sqrt(2.25 / 3.0))


def test_filing_record_rejects_naive_acceptance_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FilingRecord(
            accession_number="0000320193-25-000079",
            cik=320193,
            form="10-Q",
            filing_date=date(2025, 2, 1),
            acceptance_datetime=datetime(2025, 2, 1, 18),
        )
