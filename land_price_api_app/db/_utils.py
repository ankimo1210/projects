"""db/_utils.py — DB 操作共通ユーティリティ。"""
from __future__ import annotations

import json
from typing import Any, Optional

import duckdb
import pandas as pd

from config import get_logger

logger = get_logger(__name__)


def _get_table_columns(
    conn: duckdb.DuckDBPyConnection,
    table_name: str = "land_prices_public_notice",
) -> list[str]:
    """テーブルのカラム名リストを返す。"""
    return [row[0] for row in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ? ORDER BY ordinal_position",
        [table_name],
    ).fetchall()]


def _align_df_to_schema(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """DataFrame をテーブルスキーマに合わせて列を整列・補完する。"""
    for c in cols:
        if c not in df.columns:
            df = df.copy()
            df[c] = None
    return df[cols]


def make_location_key(lat: float, lon: float, precision: int = 5) -> str:
    """緯度経度から一意な文字列キーを生成する。"""
    return f"{lat:.{precision}f},{lon:.{precision}f}"


def _normalize_json_text(value: Any) -> str | None:
    """dict / list → JSON 文字列。文字列はそのまま返す。None → None。"""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
