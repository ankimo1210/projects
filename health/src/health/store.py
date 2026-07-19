"""DuckDB store: raw payloads, typed layer, sync state."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_json(
    endpoint VARCHAR, date_key VARCHAR, fetched_at TIMESTAMP, payload JSON,
    PRIMARY KEY(endpoint, date_key));
CREATE TABLE IF NOT EXISTS daily_series(
    metric VARCHAR, date DATE, value DOUBLE, PRIMARY KEY(metric, date));
CREATE TABLE IF NOT EXISTS sleep_sessions(
    log_id BIGINT PRIMARY KEY, date DATE, start_ts TIMESTAMP, end_ts TIMESTAMP,
    minutes_asleep INT, minutes_deep INT, minutes_light INT, minutes_rem INT,
    minutes_wake INT, efficiency INT, is_main BOOLEAN);
CREATE TABLE IF NOT EXISTS intraday(
    metric VARCHAR, ts TIMESTAMP, value DOUBLE, PRIMARY KEY(metric, ts));
CREATE TABLE IF NOT EXISTS sync_state(
    metric VARCHAR PRIMARY KEY, last_synced_date DATE, status VARCHAR,
    updated_at TIMESTAMP);
"""

_SLEEP_COLS = ["log_id", "date", "start_ts", "end_ts", "minutes_asleep", "minutes_deep",
               "minutes_light", "minutes_rem", "minutes_wake", "efficiency", "is_main"]


class Store:
    def __init__(self, db_path: str | Path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(db_path))
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                self.con.execute(stmt)

    def close(self) -> None:
        self.con.close()

    # -- writes ------------------------------------------------------------
    def upsert_raw(self, endpoint: str, date_key: str, payload: Any) -> None:
        self.con.execute(
            "INSERT INTO raw_json VALUES (?, ?, now(), ?) "
            "ON CONFLICT DO UPDATE SET payload = excluded.payload, fetched_at = now()",
            [endpoint, date_key, json.dumps(payload)])

    def upsert_daily(self, rows) -> None:
        rows = list(rows)
        if rows:
            self.con.executemany(
                "INSERT INTO daily_series VALUES (?, ?, ?) "
                "ON CONFLICT DO UPDATE SET value = excluded.value", rows)

    def upsert_sleep(self, rows) -> None:
        for r in rows:
            self.con.execute(
                f"INSERT INTO sleep_sessions VALUES ({', '.join('?' * len(_SLEEP_COLS))}) "
                "ON CONFLICT DO UPDATE SET minutes_asleep = excluded.minutes_asleep, "
                "efficiency = excluded.efficiency",
                [r[c] for c in _SLEEP_COLS])

    def upsert_intraday(self, rows) -> None:
        rows = list(rows)
        if rows:
            self.con.executemany(
                "INSERT INTO intraday VALUES (?, ?, ?) "
                "ON CONFLICT DO UPDATE SET value = excluded.value", rows)

    # -- sync state --------------------------------------------------------
    def get_sync_state(self, metric: str) -> date | None:
        row = self.con.execute(
            "SELECT last_synced_date FROM sync_state WHERE metric = ?", [metric]).fetchone()
        return row[0] if row else None

    def set_sync_state(self, metric: str, last_synced: date, status: str = "ok") -> None:
        self.con.execute(
            "INSERT OR REPLACE INTO sync_state VALUES (?, ?, ?, now())",
            [metric, last_synced, status])

    def sync_states(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, last_synced_date, status FROM sync_state ORDER BY metric").df()

    # -- reads -------------------------------------------------------------
    def series_stats(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, count(*) AS n, min(date) AS first_date, max(date) AS last_date "
            "FROM daily_series GROUP BY metric ORDER BY metric").df()

    def daily_frame(self, metrics: list[str]) -> pd.DataFrame:
        ph = ", ".join("?" * len(metrics))
        df = self.con.execute(
            f"SELECT date, metric, value FROM daily_series WHERE metric IN ({ph}) "
            "ORDER BY date", metrics).df()
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
            "SELECT ts, value FROM intraday WHERE metric = ? AND CAST(ts AS DATE) = ? "
            "ORDER BY ts", [metric, day]).df()
