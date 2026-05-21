"""
ui.unit_price
平米単価を主表示にしつつ、補助表示として坪単価を添えるための小さなヘルパー。
"""
from __future__ import annotations

import pandas as pd

SQM_PER_TSUBO = 3.305785


def yen_per_sqm_to_tsubo(value) -> float | None:
    """円/m² を 円/坪 に換算する。"""
    if value is None or pd.isna(value):
        return None
    return float(value) * SQM_PER_TSUBO


def yen_per_sqm_to_tsubo_man(value) -> float | None:
    """円/m² を 万円/坪 に換算する。表の補助列向け。"""
    tsubo = yen_per_sqm_to_tsubo(value)
    return None if tsubo is None else tsubo / 10_000


def yen_to_man(value) -> float | None:
    """円を万円に換算する。"""
    if value is None or pd.isna(value):
        return None
    return float(value) / 10_000


def format_yen_per_sqm_with_tsubo(value, *, yen_symbol: bool = True) -> str:
    """例: 10.0万円/m²（33.1万円/坪）"""
    sqm_man = yen_to_man(value)
    tsubo_man = yen_per_sqm_to_tsubo_man(value)
    if sqm_man is None or tsubo_man is None:
        return "—"
    return f"{sqm_man:,.1f}万円/m²（{tsubo_man:,.1f}万円/坪）"


def format_yen_per_sqm_and_tsubo_jp(value) -> str:
    """例: 10.0万円/m²（33.1万円/坪）"""
    return format_yen_per_sqm_with_tsubo(value, yen_symbol=False)


def convert_yen_columns_to_man(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """円単位の列を表示用に万円単位へ変換したコピーを返す。"""
    result = df.copy()
    for col in columns:
        if col in result.columns:
            result[col] = result[col].map(yen_to_man)
    return result


def format_man(value) -> str:
    """万円値を小数1桁で表示する。"""
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.1f}"


def add_tsubo_price_column(
    df: pd.DataFrame,
    source_col: str,
    target_col: str,
) -> pd.DataFrame:
    """source_col の直後に坪単価列（万円/坪）を追加したコピーを返す。"""
    result = df.copy()
    if source_col not in result.columns or target_col in result.columns:
        return result
    pos = list(result.columns).index(source_col) + 1
    result.insert(pos, target_col, result[source_col].map(yen_per_sqm_to_tsubo_man))
    return result
