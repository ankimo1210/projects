"""
utils.py
アプリ全体で使う汎用ユーティリティ関数。

NaN / None の安全な型変換を一元管理する。
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def safe_str(v: Any, fallback: str = "—") -> str:
    """NaN / None / 空文字列を fallback に変換して str を返す。"""
    if v is None:
        return fallback
    if isinstance(v, float) and pd.isna(v):
        return fallback
    try:
        import numpy as np

        if isinstance(v, np.floating) and np.isnan(float(v)):
            return fallback
    except Exception:
        pass
    s = str(v).strip()
    return s if s and s not in ("nan", "None", "NaT", "nat") else fallback


def safe_float(v: Any) -> float | None:
    """NaN / None → None、それ以外は float に変換する。"""
    if v is None:
        return None
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def safe_int(v: Any) -> int | None:
    """NaN / None → None、それ以外は int に変換する。"""
    f = safe_float(v)
    return None if f is None else int(f)


def is_nan(v: Any) -> bool:
    """値が None または NaN であれば True。"""
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except Exception:
        return False
