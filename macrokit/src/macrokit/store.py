"""DuckDB store. One row per observation *vintage*, never one row per period.

The whole point of this table is that a period can hold several values -- the
flash estimate and each revision -- each tagged with when it was released. Code
that wants "the current value" asks `pit.latest`; code that wants "what was
knowable then" asks `pit.as_of`.

`vintage_kind` records how much to trust `release_date`:
  actual    -- the source published the release date (ALFRED, US Treasury)
  snapshot  -- reconstructed from when we fetched it (every Japanese source)
  estimated -- inferred from a publication lag; weakest of the three
"""

from __future__ import annotations

from dataclasses import astuple, dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

VINTAGE_KINDS = frozenset({"actual", "snapshot", "estimated"})

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS observations (
  indicator     VARCHAR   NOT NULL,
  period_start  DATE      NOT NULL,
  period_end    DATE      NOT NULL,
  release_date  TIMESTAMPTZ NOT NULL,
  vintage_seq   INTEGER   NOT NULL,
  value         DOUBLE    NOT NULL,
  unit          VARCHAR   NOT NULL,
  sa            VARCHAR   NOT NULL,
  freq          VARCHAR   NOT NULL,
  source        VARCHAR   NOT NULL,
  source_url    VARCHAR   NOT NULL,
  ingested_at   TIMESTAMPTZ NOT NULL,
  vintage_kind  VARCHAR   NOT NULL,
  PRIMARY KEY (indicator, period_start, release_date)
);

CREATE TABLE IF NOT EXISTS components (
  indicator      VARCHAR NOT NULL,
  component_code VARCHAR NOT NULL,
  component_name VARCHAR NOT NULL,
  weight         DOUBLE,
  period_start   DATE    NOT NULL,
  release_date   TIMESTAMPTZ NOT NULL,
  value          DOUBLE,
  PRIMARY KEY (indicator, component_code, period_start, release_date)
);

CREATE TABLE IF NOT EXISTS market_rates (
  curve       VARCHAR NOT NULL,
  obs_date    DATE    NOT NULL,
  tenor_y     DOUBLE  NOT NULL,
  yield_pct   DOUBLE  NOT NULL,
  source      VARCHAR NOT NULL,
  source_url  VARCHAR NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (curve, obs_date, tenor_y)
);

CREATE TABLE IF NOT EXISTS releases (
  indicator     VARCHAR     NOT NULL,
  period_start  DATE        NOT NULL,
  period_end    DATE        NOT NULL,
  release_kind  VARCHAR     NOT NULL,
  release_date  TIMESTAMPTZ NOT NULL,
  scheduled     BOOLEAN     NOT NULL,
  source        VARCHAR     NOT NULL,
  source_url    VARCHAR     NOT NULL,
  ingested_at   TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (indicator, period_start, release_kind)
);

CREATE TABLE IF NOT EXISTS expectations (
  indicator     VARCHAR NOT NULL,
  period_start  DATE    NOT NULL,
  release_kind  VARCHAR NOT NULL,
  method        VARCHAR NOT NULL,
  expected      DOUBLE  NOT NULL,
  as_of         DATE    NOT NULL,
  source        VARCHAR NOT NULL,
  source_url    VARCHAR NOT NULL,
  ingested_at   TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (indicator, period_start, release_kind, method)
);
"""

RELEASE_KINDS = frozenset({"1st_prelim", "2nd_prelim", "2nd_prelim_revised"})
EXPECTATION_METHODS = frozenset({"prior_vintage", "random_walk", "ar_model", "esp"})


@dataclass(frozen=True)
class Observation:
    indicator: str
    period_start: date
    period_end: date
    release_date: datetime
    vintage_seq: int
    value: float
    unit: str
    sa: str
    freq: str
    source: str
    source_url: str
    ingested_at: datetime
    vintage_kind: str


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open (creating if needed) the database and ensure the schema exists.

    Pins the session timezone to Asia/Tokyo. DuckDB renders a stored
    TIMESTAMPTZ (``release_date``, ``ingested_at``) in whatever the session
    timezone happens to be, and this pipeline decides *which Tokyo calendar
    day* a release falls on from that rendered value (`panel.py`'s
    ``release_date.date()``, `expectations.py`'s business-day lookups). Left
    unset, the session timezone defaults to the OS's local zone, so the same
    database would silently assign releases to different -- sometimes wrong
    -- Tokyo days depending on the host's TZ. Pinning it here makes every
    caller's view of "the day" agree, regardless of where `connect` runs.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("SET TimeZone='Asia/Tokyo'")
    con.execute(SCHEMA_SQL)
    return con


def _is_naive(dt: datetime) -> bool:
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


def _reject_naive(row: Observation, field: str, value: datetime) -> None:
    if _is_naive(value):
        raise ValueError(
            f"{row.indicator} {row.period_start}: {field} must be a timezone-aware "
            f"datetime, got a naive one ({value!r}). A naive value would be stored "
            "after DuckDB reinterprets it in the local session timezone, and later "
            "comparisons against aware datetimes (e.g. in pit.as_of) would raise a "
            "confusing TypeError instead of failing here with a clear message."
        )


def _validate(row: Observation) -> None:
    _reject_naive(row, "release_date", row.release_date)
    _reject_naive(row, "ingested_at", row.ingested_at)
    if row.vintage_kind not in VINTAGE_KINDS:
        raise ValueError(f"unknown vintage_kind: {row.vintage_kind}")
    if row.vintage_kind == "snapshot" and row.release_date > row.ingested_at:
        raise ValueError(
            f"{row.indicator} {row.period_start}: snapshot has release_date after "
            f"ingested_at ({row.release_date} > {row.ingested_at})"
        )


def insert_observations(con: duckdb.DuckDBPyConnection, rows: list[Observation]) -> int:
    """Insert rows, ignoring ones already present. Returns the number inserted."""
    for row in rows:
        _validate(row)
    before = con.execute("SELECT count(*) FROM observations").fetchone()[0]
    con.executemany(
        "INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [astuple(row) for row in rows],
    )
    after = con.execute("SELECT count(*) FROM observations").fetchone()[0]
    return after - before


def recompute_vintage_seq(con: duckdb.DuckDBPyConnection, indicator: str) -> None:
    """Renumber ``vintage_seq`` for one indicator to mean 公表順 (1st published = 1,
    2nd = 2, ...), by publication order (``release_date``) within each period.

    A window function over the whole table, not a per-row counter maintained at
    insert time: `sources/esri_gdp.py` used to hard-code ``vintage_seq`` from
    ``release_kind`` alone (1st_prelim -> 1, everything else -> 2), which is
    wrong for every period below the release actually being ingested -- each
    ESRI table carries the series back to 1994, so a single 2nd_prelim fetch
    stamped ``vintage_seq=2`` onto ~19 rows most of which were already at
    vintage 3, 4, 5... A window recompute is order-independent (safe to re-run
    after a partial backfill) and self-correcting (a later out-of-order insert
    fixes every affected row, not just the one just inserted), where an
    insert-time counter would depend on ingesting oldest-first and silently
    drift on a partial re-run.

    Scoped to ``indicator`` so it cannot touch ALFRED-sourced rows, which
    already get a correct per-period sequence from `sources/alfred.py` (each
    realtime-window fetch returns every vintage for a period in one response,
    counted in order there).
    """
    con.execute(
        """
        UPDATE observations
        SET vintage_seq = sub.rn
        FROM (
            SELECT period_start, release_date,
                   row_number() OVER (
                       PARTITION BY period_start ORDER BY release_date
                   ) AS rn
            FROM observations
            WHERE indicator = ?
        ) AS sub
        WHERE observations.indicator = ?
          AND observations.period_start = sub.period_start
          AND observations.release_date = sub.release_date
        """,
        [indicator, indicator],
    )


@dataclass(frozen=True)
class RateObservation:
    curve: str
    obs_date: date
    tenor_y: float
    yield_pct: float
    source: str
    source_url: str
    ingested_at: datetime


def insert_rates(con: duckdb.DuckDBPyConnection, rows: list[RateObservation]) -> int:
    """Insert rate observations, ignoring rows whose key is already present."""
    if not rows:
        return 0
    for row in rows:
        if _is_naive(row.ingested_at):
            raise ValueError(
                f"insert_rates: ingested_at must be timezone-aware, got {row.ingested_at!r}"
            )
    before = con.execute("SELECT count(*) FROM market_rates").fetchone()[0]
    con.executemany(
        "INSERT OR IGNORE INTO market_rates VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (r.curve, r.obs_date, r.tenor_y, r.yield_pct, r.source, r.source_url, r.ingested_at)
            for r in rows
        ],
    )
    after = con.execute("SELECT count(*) FROM market_rates").fetchone()[0]
    return after - before


@dataclass(frozen=True)
class ReleaseEvent:
    indicator: str
    period_start: date
    period_end: date
    release_kind: str
    release_date: datetime
    scheduled: bool
    source: str
    source_url: str
    ingested_at: datetime


def insert_releases(con: duckdb.DuckDBPyConnection, rows: list[ReleaseEvent]) -> int:
    """Insert release events, ignoring rows whose key is already present."""
    if not rows:
        return 0
    for row in rows:
        if _is_naive(row.release_date):
            raise ValueError(
                f"insert_releases: release_date must be timezone-aware, got {row.release_date!r}"
            )
        if _is_naive(row.ingested_at):
            raise ValueError(
                f"insert_releases: ingested_at must be timezone-aware, got {row.ingested_at!r}"
            )
        if row.release_kind not in RELEASE_KINDS:
            raise ValueError(f"unknown release_kind: {row.release_kind}")
    before = con.execute("SELECT count(*) FROM releases").fetchone()[0]
    con.executemany(
        "INSERT OR IGNORE INTO releases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [astuple(row) for row in rows],
    )
    after = con.execute("SELECT count(*) FROM releases").fetchone()[0]
    return after - before


@dataclass(frozen=True)
class Expectation:
    indicator: str
    period_start: date
    release_kind: str
    method: str
    expected: float
    as_of: date
    source: str
    source_url: str
    ingested_at: datetime


def insert_expectations(con: duckdb.DuckDBPyConnection, rows: list[Expectation]) -> int:
    """Insert expectation rows, ignoring rows whose key is already present."""
    if not rows:
        return 0
    for row in rows:
        if _is_naive(row.ingested_at):
            raise ValueError(
                f"insert_expectations: ingested_at must be timezone-aware, got {row.ingested_at!r}"
            )
        if row.method not in EXPECTATION_METHODS:
            raise ValueError(f"unknown method: {row.method}")
    before = con.execute("SELECT count(*) FROM expectations").fetchone()[0]
    con.executemany(
        "INSERT OR IGNORE INTO expectations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [astuple(row) for row in rows],
    )
    after = con.execute("SELECT count(*) FROM expectations").fetchone()[0]
    return after - before
