"""Shared test builders for the expectations and event-panel test suites.

`test_expectations.py` and Task 7's event-panel tests both need the same
minimal fixtures: a fresh in-memory-ish DuckDB connection, one observation
vintage, one release event, and a run of `market_rates` business days. Kept
here instead of defined inline in one test module and imported by the other,
so neither test module depends on the other's internals.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from macrokit import store

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


@pytest.fixture
def con(tmp_path):
    return store.connect(tmp_path / "t.duckdb")


def _obs(con, period_start, release_date, value, seq):
    store.insert_observations(con, [store.Observation(
        indicator="jp_real_gdp_qoq_saar", period_start=period_start,
        period_end=date(period_start.year, period_start.month + 2, 30),
        release_date=release_date, vintage_seq=seq, value=value,
        unit="percent_saar", sa="sa", freq="Q", source="esri_gdp",
        source_url="u", ingested_at=NOW, vintage_kind="actual",
    )])


def _event(period_start, kind, release_date):
    return store.ReleaseEvent(
        indicator="jp_real_gdp_qoq_saar", period_start=period_start,
        period_end=date(period_start.year, period_start.month + 2, 30),
        release_kind=kind, release_date=release_date, scheduled=False,
        source="esri_calendar", source_url="u", ingested_at=NOW,
    )


def _rates(con, *days):
    store.insert_rates(con, [store.RateObservation(
        curve="jgb", obs_date=d, tenor_y=10.0, yield_pct=2.9,
        source="mof_jgb", source_url="u", ingested_at=NOW,
    ) for d in days])
