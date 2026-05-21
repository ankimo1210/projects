"""DuckDB client: schema management, upsert, queries."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

# project root is 3 levels up: src/storage/duckdb_client.py → src/storage → src → root
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_DB = _PROJECT_ROOT / "data" / "market.duckdb"


_CREATE_PRICES = """
CREATE TABLE IF NOT EXISTS prices (
    timestamp   TIMESTAMP NOT NULL,
    ticker      VARCHAR   NOT NULL,
    asset_class VARCHAR,
    market      VARCHAR,
    frequency   VARCHAR   NOT NULL DEFAULT '1d',
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      DOUBLE,
    source      VARCHAR,
    updated_at  TIMESTAMP DEFAULT now(),
    PRIMARY KEY (timestamp, ticker, frequency)
)
"""

_CREATE_INDICATORS = """
CREATE TABLE IF NOT EXISTS indicators (
    timestamp      TIMESTAMP NOT NULL,
    ticker         VARCHAR   NOT NULL,
    indicator_name VARCHAR   NOT NULL,
    win            INTEGER,
    value          DOUBLE,
    updated_at     TIMESTAMP DEFAULT now(),
    PRIMARY KEY (timestamp, ticker, indicator_name, win)
)
"""

_CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    timestamp    TIMESTAMP NOT NULL,
    ticker       VARCHAR   NOT NULL,
    signal_name  VARCHAR   NOT NULL,
    signal_value DOUBLE,
    score        DOUBLE,
    direction    VARCHAR,
    reason       VARCHAR,
    created_at   TIMESTAMP DEFAULT now(),
    PRIMARY KEY (timestamp, ticker, signal_name)
)
"""

_CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id      VARCHAR PRIMARY KEY,
    ticker        VARCHAR,
    condition_type VARCHAR,
    threshold     DOUBLE,
    current_value DOUBLE,
    status        VARCHAR DEFAULT 'active',
    triggered_at  TIMESTAMP,
    message       VARCHAR
)
"""


class DuckDBClient:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else _DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        conn = self._conn
        conn.execute(_CREATE_PRICES)
        conn.execute(_CREATE_INDICATORS)
        conn.execute(_CREATE_SIGNALS)
        conn.execute(_CREATE_ALERTS)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------

    def upsert_prices(self, df: pd.DataFrame) -> None:
        """Insert or replace price rows. df must have columns matching prices table."""
        conn = self.connect()
        conn.execute("""
            INSERT OR REPLACE INTO prices
            SELECT * FROM df
        """)

    def get_prices(
        self,
        tickers: list[str],
        frequency: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        conn = self.connect()
        tickers_sql = ", ".join(f"'{t}'" for t in tickers)
        where = [f"ticker IN ({tickers_sql})", f"frequency = '{frequency}'"]
        if start:
            where.append(f"timestamp >= '{start}'")
        if end:
            where.append(f"timestamp <= '{end}'")
        query = f"SELECT * FROM prices WHERE {' AND '.join(where)} ORDER BY timestamp"
        return conn.execute(query).df()

    def get_latest_timestamp(self, ticker: str, frequency: str = "1d") -> str | None:
        conn = self.connect()
        result = conn.execute(
            "SELECT MAX(timestamp) FROM prices WHERE ticker = ? AND frequency = ?",
            [ticker, frequency],
        ).fetchone()
        if result and result[0]:
            return str(result[0])[:10]
        return None

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------

    def upsert_indicators(self, df: pd.DataFrame) -> None:
        conn = self.connect()
        conn.execute("INSERT OR REPLACE INTO indicators SELECT * FROM df")

    def get_indicators(
        self,
        tickers: list[str],
        indicator_names: list[str] | None = None,
        start: str | None = None,
    ) -> pd.DataFrame:
        conn = self.connect()
        tickers_sql = ", ".join(f"'{t}'" for t in tickers)
        where = [f"ticker IN ({tickers_sql})"]
        if indicator_names:
            names_sql = ", ".join(f"'{n}'" for n in indicator_names)
            where.append(f"indicator_name IN ({names_sql})")
        if start:
            where.append(f"timestamp >= '{start}'")
        query = f"SELECT * FROM indicators WHERE {' AND '.join(where)} ORDER BY timestamp"
        return conn.execute(query).df()

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def upsert_signals(self, df: pd.DataFrame) -> None:
        conn = self.connect()
        conn.execute("INSERT OR REPLACE INTO signals SELECT * FROM df")

    def get_signals(
        self, tickers: list[str] | None = None, latest_only: bool = True
    ) -> pd.DataFrame:
        conn = self.connect()
        where = []
        if tickers:
            tickers_sql = ", ".join(f"'{t}'" for t in tickers)
            where.append(f"ticker IN ({tickers_sql})")
        where_clause = f"WHERE {' AND '.join(where)}" if where else ""

        if latest_only:
            query = f"""
                SELECT * FROM signals {where_clause}
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY ticker, signal_name ORDER BY timestamp DESC
                ) = 1
                ORDER BY score DESC
            """
        else:
            query = f"SELECT * FROM signals {where_clause} ORDER BY timestamp DESC"
        return conn.execute(query).df()

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def upsert_alerts(self, df: pd.DataFrame) -> None:
        conn = self.connect()
        conn.execute("INSERT OR REPLACE INTO alerts SELECT * FROM df")

    def get_active_alerts(self) -> pd.DataFrame:
        conn = self.connect()
        return conn.execute(
            "SELECT * FROM alerts WHERE status = 'active' ORDER BY triggered_at DESC"
        ).df()

    def dismiss_alert(self, alert_id: str) -> None:
        conn = self.connect()
        conn.execute("UPDATE alerts SET status = 'dismissed' WHERE alert_id = ?", [alert_id])

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def execute(self, query: str, params=None) -> pd.DataFrame:
        conn = self.connect()
        if params:
            return conn.execute(query, params).df()
        return conn.execute(query).df()
