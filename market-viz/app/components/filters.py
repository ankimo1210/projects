"""Sidebar filter helpers."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st
import yaml


@st.cache_data
def load_instruments() -> list[dict]:
    with open("src/config/instruments.yaml") as f:
        cfg = yaml.safe_load(f)
    result: list[dict] = []
    for group in cfg.get("instruments", {}).values():
        result.extend(group)
    return result


def get_ticker_options() -> list[str]:
    return [i["ticker"] for i in load_instruments()]


def date_range_filter(
    label: str = "期間",
    default_days: int = 365,
    key: str = "date_range",
) -> tuple[date, date]:
    end_date = date.today()
    start_date = end_date - timedelta(days=default_days)
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("開始日", value=start_date, key=f"{key}_start")
    with col2:
        end = st.date_input("終了日", value=end_date, key=f"{key}_end")
    return start, end


def interval_selector(key: str = "interval") -> str:
    return st.selectbox(
        "時間軸",
        options=["1d", "1wk", "1mo"],
        index=0,
        key=key,
    )
