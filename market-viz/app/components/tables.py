"""Styled DataFrame renderers for Streamlit."""

from __future__ import annotations

import pandas as pd


def _pct_color(val: float) -> str:
    if pd.isna(val):
        return ""
    return "color: #26a69a" if val >= 0 else "color: #ef5350"


def _zscore_color(val: float) -> str:
    if pd.isna(val):
        return ""
    if val >= 2.0:
        return "color: #ff9800; font-weight: bold"
    if val <= -2.0:
        return "color: #42a5f5; font-weight: bold"
    if abs(val) >= 1.5:
        return "color: #ffee58"
    return ""


def style_dashboard_df(df: pd.DataFrame) -> "pd.Styler":
    pct_cols = [c for c in df.columns if c.startswith("ret_")]
    z_cols = [c for c in df.columns if c.startswith("zscore_")]

    style = df.style
    for col in pct_cols:
        style = style.applymap(_pct_color, subset=[col])
    for col in z_cols:
        style = style.applymap(_zscore_color, subset=[col])

    # format
    fmt: dict[str, str] = {}
    for col in pct_cols:
        fmt[col] = "{:.2%}"
    for col in z_cols:
        fmt[col] = "{:.2f}"
    for col in df.columns:
        if col.startswith("vol_"):
            fmt[col] = "{:.2%}"
        if col.startswith("pct_"):
            fmt[col] = "{:.0f}%"
        if col in ("current_dd", "max_dd"):
            fmt[col] = "{:.2%}"

    style = style.format(fmt, na_rep="-")
    return style
