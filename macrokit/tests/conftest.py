"""Shared test fixtures for the expectations and event-panel test suites.

`test_expectations.py` and Task 7's event-panel tests both need the same
minimal building blocks: a fresh DuckDB connection, one observation vintage,
one release event, and a run of `market_rates` business days.

A conftest is auto-discovered by pytest regardless of which directory the
run starts from. That property matters here: a plain `helpers.py` module is
not importable under this workspace's `--import-mode=importlib` (it does
not prepend the tests directory to `sys.path` the way the default "prepend"
mode does), and pinning it with a `pythonpath` ini entry only works when
pytest actually loads `macrokit/pyproject.toml` -- a run started from the
repo root loads the root `pyproject.toml` instead, and the import breaks.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from macrokit import store

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


@pytest.fixture
def con(tmp_path):
    return store.connect(tmp_path / "t.duckdb")


@pytest.fixture
def insert_obs(con):
    """Insert one GDP observation vintage."""

    def _insert(period_start, release_date, value, seq):
        store.insert_observations(con, [store.Observation(
            indicator="jp_real_gdp_qoq_saar", period_start=period_start,
            period_end=date(period_start.year, period_start.month + 2, 30),
            release_date=release_date, vintage_seq=seq, value=value,
            unit="percent_saar", sa="sa", freq="Q", source="esri_gdp",
            source_url="u", ingested_at=NOW, vintage_kind="actual",
        )])

    return _insert


@pytest.fixture
def insert_rates(con):
    """Insert a 10y rate row for each given date."""

    def _insert(*days):
        store.insert_rates(con, [store.RateObservation(
            curve="jgb", obs_date=d, tenor_y=10.0, yield_pct=2.9,
            source="mof_jgb", source_url="u", ingested_at=NOW,
        ) for d in days])

    return _insert


@pytest.fixture
def make_event():
    """Build a ReleaseEvent for one period and kind."""

    def _make(period_start, kind, release_date):
        return store.ReleaseEvent(
            indicator="jp_real_gdp_qoq_saar", period_start=period_start,
            period_end=date(period_start.year, period_start.month + 2, 30),
            release_kind=kind, release_date=release_date, scheduled=False,
            source="esri_calendar", source_url="u", ingested_at=NOW,
        )

    return _make
