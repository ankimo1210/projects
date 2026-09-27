"""DuckDB-backed local cache for price history and macro time series.

Tables:
  prices(symbol TEXT, date DATE, open DOUBLE, high DOUBLE, low DOUBLE,
         close DOUBLE, adj_close DOUBLE, volume DOUBLE,
         PRIMARY KEY(symbol, date))
  macro_series(series_id TEXT, date DATE, value DOUBLE,
               PRIMARY KEY(series_id, date))
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pandas as pd

_DEFAULT_DIR = Path(
    os.environ.get("STOCKKIT_DATA_DIR", Path(__file__).resolve().parents[3] / "_data")
)
_DB_NAME = "cache.duckdb"


def db_path() -> Path:
    _DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_DIR / _DB_NAME


@contextmanager
def connect() -> Iterator[duckdb.DuckDBPyConnection]:
    con = duckdb.connect(str(db_path()))
    try:
        _ensure_schema(con)
        yield con
    finally:
        con.close()


def _ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            symbol VARCHAR,
            date DATE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            adj_close DOUBLE,
            volume DOUBLE,
            PRIMARY KEY (symbol, date)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS macro_series (
            series_id VARCHAR,
            date DATE,
            value DOUBLE,
            PRIMARY KEY (series_id, date)
        )
        """
    )


def read_prices(symbol: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    with connect() as con:
        q = "SELECT date, open, high, low, close, adj_close, volume FROM prices WHERE symbol = ?"
        params: list = [symbol]
        if start:
            q += " AND date >= ?"
            params.append(start)
        if end:
            q += " AND date <= ?"
            params.append(end)
        q += " ORDER BY date"
        df = con.execute(q, params).df()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    return df


def upsert_prices(symbol: str, df: pd.DataFrame) -> int:
    """Insert/replace prices for symbol. Returns row count written."""
    if df.empty:
        return 0
    out = df.copy()
    out = out.reset_index().rename(columns={"index": "date"})
    if "Date" in out.columns:
        out = out.rename(columns={"Date": "date"})
    out["date"] = pd.to_datetime(out["date"]).dt.date
    out["symbol"] = symbol
    out = out[["symbol", "date", "open", "high", "low", "close", "adj_close", "volume"]]
    with connect() as con:
        con.register("incoming", out)
        con.execute(
            """
            INSERT OR REPLACE INTO prices
            SELECT * FROM incoming
            """
        )
    return len(out)


def latest_cached_date(symbol: str) -> pd.Timestamp | None:
    with connect() as con:
        row = con.execute("SELECT max(date) FROM prices WHERE symbol = ?", [symbol]).fetchone()
    if row and row[0]:
        return pd.Timestamp(row[0])
    return None


# ---------- macro_series ----------


def read_macro(series_id: str, start: str | None = None, end: str | None = None) -> pd.Series:
    with connect() as con:
        q = "SELECT date, value FROM macro_series WHERE series_id = ?"
        params: list = [series_id]
        if start:
            q += " AND date >= ?"
            params.append(start)
        if end:
            q += " AND date <= ?"
            params.append(end)
        q += " ORDER BY date"
        df = con.execute(q, params).df()
    if df.empty:
        return pd.Series(dtype=float, name=series_id)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].rename(series_id)


def upsert_macro(series_id: str, series: pd.Series) -> int:
    if series.empty:
        return 0
    df = series.reset_index()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["series_id"] = series_id
    df = df[["series_id", "date", "value"]].dropna(subset=["value"])
    with connect() as con:
        con.register("incoming_macro", df)
        con.execute("INSERT OR REPLACE INTO macro_series SELECT * FROM incoming_macro")
    return len(df)


def latest_macro_date(series_id: str) -> pd.Timestamp | None:
    with connect() as con:
        row = con.execute(
            "SELECT max(date) FROM macro_series WHERE series_id = ?", [series_id]
        ).fetchone()
    if row and row[0]:
        return pd.Timestamp(row[0])
    return None
