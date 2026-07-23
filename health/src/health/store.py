"""DuckDB store: raw payloads, typed layer, sync state, transactional chunk replacement."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from health.endpoints import Metric, ParsedRows

SYNC_OK = "ok"
SYNC_IN_PROGRESS = "in_progress"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_json(
    metric VARCHAR, range_start DATE, range_end DATE, page_index INTEGER,
    fetched_at TIMESTAMP, payload JSON,
    PRIMARY KEY(metric, range_start, range_end, page_index));
CREATE TABLE IF NOT EXISTS daily_series(
    metric VARCHAR, date DATE, value DOUBLE, PRIMARY KEY(metric, date));
CREATE TABLE IF NOT EXISTS sleep_sessions(
    provider_id VARCHAR PRIMARY KEY, date DATE, start_ts TIMESTAMP, end_ts TIMESTAMP,
    minutes_asleep INTEGER, minutes_deep INTEGER, minutes_light INTEGER,
    minutes_rem INTEGER, minutes_wake INTEGER, efficiency INTEGER, is_main BOOLEAN);
CREATE TABLE IF NOT EXISTS intraday(
    metric VARCHAR, ts TIMESTAMP, value DOUBLE, PRIMARY KEY(metric, ts));
CREATE TABLE IF NOT EXISTS sync_state(
    metric VARCHAR PRIMARY KEY, last_synced_date DATE, status VARCHAR,
    updated_at TIMESTAMP);
"""

_SLEEP_COLS = [
    "provider_id",
    "date",
    "start_ts",
    "end_ts",
    "minutes_asleep",
    "minutes_deep",
    "minutes_light",
    "minutes_rem",
    "minutes_wake",
    "efficiency",
    "is_main",
]


class Store:
    def __init__(self, db_path: str | Path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(db_path))
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                self.con.execute(stmt)

    def close(self) -> None:
        self.con.close()

    # -- low-level writes (seed script / legacy tests; sync engine uses
    # replace_chunk instead) -------------------------------------------------
    def upsert_daily(self, rows) -> None:
        rows = list(rows)
        if rows:
            self.con.executemany(
                "INSERT INTO daily_series VALUES (?, ?, ?) "
                "ON CONFLICT DO UPDATE SET value = excluded.value",
                rows,
            )

    def upsert_sleep(self, rows) -> None:
        set_clause = ", ".join(f"{c} = excluded.{c}" for c in _SLEEP_COLS if c != "provider_id")
        for r in rows:
            self.con.execute(
                f"INSERT INTO sleep_sessions VALUES ({', '.join('?' * len(_SLEEP_COLS))}) "
                f"ON CONFLICT DO UPDATE SET {set_clause}",
                [r[c] for c in _SLEEP_COLS],
            )

    def upsert_intraday(self, rows) -> None:
        rows = list(rows)
        if rows:
            self.con.executemany(
                "INSERT INTO intraday VALUES (?, ?, ?) "
                "ON CONFLICT DO UPDATE SET value = excluded.value",
                rows,
            )

    # -- transactional chunk replacement --------------------------------------
    def replace_chunk(
        self,
        metric: Metric,
        start: date,
        end: date,
        payloads: Sequence[dict],
        rows: ParsedRows,
        *,
        status: str = SYNC_OK,
    ) -> None:
        """Atomically replace one (metric, start, end) chunk: old raw pages,
        old typed rows in range, and the watermark all move together so a
        stale page, an upstream deletion, or a mid-parse failure never leaves
        raw/typed/watermark inconsistent with each other."""
        series = list(metric.series_names)
        series_ph = ", ".join("?" * len(series))
        con = self.con
        con.execute("BEGIN TRANSACTION")
        try:
            # 1. drop old raw pages for this exact chunk, 2. insert the new ones
            con.execute(
                "DELETE FROM raw_json WHERE metric = ? AND range_start = ? AND range_end = ?",
                [metric.name, start, end],
            )
            for page_index, payload in enumerate(payloads):
                con.execute(
                    "INSERT INTO raw_json VALUES (?, ?, ?, ?, now(), ?)",
                    [metric.name, start, end, page_index, json.dumps(payload)],
                )
            # 3. drop typed rows for this metric's series within the range, but
            # only in the ONE table this metric actually writes to. A given
            # series name is not unique across tables -- e.g. "steps" (daily
            # rollup) and "intraday_steps" (reconcile intraday) both have
            # series_names == ("steps",) -- so the target table must come from
            # the metric's own identity (full_history=False marks the two
            # intraday-cadence metrics), never from which fields of `rows`
            # happen to be non-empty on this particular call: an empty-payload
            # replacement must still clear stale rows in the metric's real
            # table.
            if metric.full_history:
                con.execute(
                    f"DELETE FROM daily_series WHERE metric IN ({series_ph}) "
                    "AND date BETWEEN ? AND ?",
                    [*series, start, end],
                )
            else:
                con.execute(
                    f"DELETE FROM intraday WHERE metric IN ({series_ph}) "
                    "AND CAST(ts AS DATE) BETWEEN ? AND ?",
                    [*series, start, end],
                )
            # 4. sleep sessions are keyed by wake date, not series name
            if metric.name == "sleep":
                con.execute("DELETE FROM sleep_sessions WHERE date BETWEEN ? AND ?", [start, end])
            # 5. insert the freshly parsed typed rows, same table restriction as above
            if metric.full_history and rows.daily:
                con.executemany("INSERT INTO daily_series VALUES (?, ?, ?)", list(rows.daily))
            elif not metric.full_history and rows.intraday:
                con.executemany("INSERT INTO intraday VALUES (?, ?, ?)", list(rows.intraday))
            if rows.sleep:
                for r in rows.sleep:
                    con.execute(
                        f"INSERT INTO sleep_sessions VALUES ({', '.join('?' * len(_SLEEP_COLS))})",
                        [r[c] for c in _SLEEP_COLS],
                    )
            # 6. advance the watermark
            con.execute(
                "INSERT INTO sync_state VALUES (?, ?, ?, now()) "
                "ON CONFLICT DO UPDATE SET last_synced_date = excluded.last_synced_date, "
                "status = excluded.status, updated_at = excluded.updated_at",
                [metric.name, end, status],
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    # -- sync state --------------------------------------------------------
    def get_sync_state(self, metric: str) -> date | None:
        checkpoint = self.get_sync_checkpoint(metric)
        return checkpoint[0] if checkpoint else None

    def get_sync_checkpoint(self, metric: str) -> tuple[date, str] | None:
        row = self.con.execute(
            "SELECT last_synced_date, status FROM sync_state WHERE metric = ?", [metric]
        ).fetchone()
        return (row[0], row[1]) if row else None

    def set_sync_state(self, metric: str, last_synced: date, status: str = SYNC_OK) -> None:
        self.con.execute(
            "INSERT OR REPLACE INTO sync_state VALUES (?, ?, ?, now())",
            [metric, last_synced, status],
        )

    def sync_states(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, last_synced_date, status FROM sync_state ORDER BY metric"
        ).df()

    # -- reads -------------------------------------------------------------
    def series_stats(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, count(*) AS n, min(date) AS first_date, max(date) AS last_date "
            "FROM daily_series GROUP BY metric ORDER BY metric"
        ).df()

    def raw_stats(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, count(*) AS n_pages, min(range_start) AS first_range_start, "
            "max(range_end) AS last_range_end FROM raw_json GROUP BY metric "
            "ORDER BY metric"
        ).df()

    def sleep_stats(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT count(*) AS n, min(date) AS first_date, max(date) AS last_date "
            "FROM sleep_sessions"
        ).df()

    def intraday_stats(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, count(*) AS n, min(CAST(ts AS DATE)) AS first_date, "
            "max(CAST(ts AS DATE)) AS last_date FROM intraday GROUP BY metric "
            "ORDER BY metric"
        ).df()

    def daily_frame(self, metrics: list[str]) -> pd.DataFrame:
        ph = ", ".join("?" * len(metrics))
        df = self.con.execute(
            f"SELECT date, metric, value FROM daily_series WHERE metric IN ({ph}) ORDER BY date",
            metrics,
        ).df()
        if df.empty:
            return pd.DataFrame(columns=["date", *metrics])
        wide = df.pivot(index="date", columns="metric", values="value").reset_index()
        for m in metrics:
            if m not in wide.columns:
                wide[m] = float("nan")
        return wide[["date", *metrics]]

    def sleep_frame(self) -> pd.DataFrame:
        return self.con.execute("SELECT * FROM sleep_sessions ORDER BY date").df()

    def intraday_frame(self, metric: str, day: date) -> pd.DataFrame:
        return self.con.execute(
            "SELECT ts, value FROM intraday WHERE metric = ? AND CAST(ts AS DATE) = ? ORDER BY ts",
            [metric, day],
        ).df()
