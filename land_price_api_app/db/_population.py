"""db/_population.py — population_stats テーブルの CRUD。"""

from __future__ import annotations

import duckdb
import pandas as pd
from config import get_logger

logger = get_logger(__name__)

_DDL_POPULATION_STATS = """
CREATE TABLE IF NOT EXISTS population_stats (
    city_code               VARCHAR NOT NULL,
    survey_year             INTEGER NOT NULL,
    total_population        BIGINT,
    households              BIGINT,
    pop_change_pct          DOUBLE,
    households_change_pct   DOUBLE,
    aging_rate              DOUBLE,
    net_migration           BIGINT,
    PRIMARY KEY (city_code, survey_year)
)
"""


def upsert_population_stats(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """population_stats テーブルに upsert する。"""
    if df.empty:
        return 0
    from db._utils import _align_df_to_schema, _get_table_columns

    for year in df["survey_year"].unique():
        conn.execute("DELETE FROM population_stats WHERE survey_year = ?", [int(year)])
    _align_df_to_schema(df, _get_table_columns(conn, "population_stats"))
    conn.execute("INSERT INTO population_stats SELECT * FROM payload")
    n = len(df)
    logger.info("population_stats upsert: %d 件", n)
    return n


def get_population_stats(conn: duckdb.DuckDBPyConnection, city_code: str) -> pd.DataFrame:
    """指定市区町村の人口統計データを年次昇順で返す。"""
    return conn.execute(
        """
        SELECT survey_year, total_population, households,
               pop_change_pct, households_change_pct, aging_rate, net_migration
        FROM population_stats
        WHERE city_code = ?
        ORDER BY survey_year ASC
        """,
        [city_code],
    ).df()


def get_population_latest(conn: duckdb.DuckDBPyConnection, city_code: str) -> dict:
    """指定市区町村の最新年の人口統計を dict で返す。データ無し時は空dict。"""
    df = conn.execute(
        """
        SELECT survey_year, total_population, households,
               pop_change_pct, households_change_pct, aging_rate, net_migration
        FROM population_stats
        WHERE city_code = ?
        ORDER BY survey_year DESC
        LIMIT 1
        """,
        [city_code],
    ).df()
    return df.iloc[0].to_dict() if not df.empty else {}
