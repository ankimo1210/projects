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
"""


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
    """Open (creating if needed) the database and ensure the schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
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
