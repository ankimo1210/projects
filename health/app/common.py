"""Shared app context: paths, cached resources, cached frames, period selector."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from health.auth import GoogleHealthAuth
from health.store import Store

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

PERIOD_OPTIONS = {"30日": 30, "90日": 90, "180日": 180, "1年": 365, "全期間": None}


@st.cache_resource
def get_store() -> Store:
    return Store(DATA_DIR / "health.duckdb")


def get_auth() -> GoogleHealthAuth:
    return GoogleHealthAuth.from_env(DATA_DIR)


@st.cache_data(ttl=300)
def load_daily(metrics: tuple[str, ...]) -> pd.DataFrame:
    return get_store().daily_frame(list(metrics))


@st.cache_data(ttl=300)
def load_sleep() -> pd.DataFrame:
    return get_store().sleep_frame()


@st.cache_data(ttl=300)
def load_intraday(metric: str, day: date) -> pd.DataFrame:
    return get_store().intraday_frame(metric, day)


def period_days(default: str = "90日") -> int | None:
    """Sidebar period selector; one shared session key across all pages."""
    labels = list(PERIOD_OPTIONS)
    sel = st.sidebar.radio("表示期間", labels, index=labels.index(default), key="period_days")
    return PERIOD_OPTIONS[sel]


def clip_days(df: pd.DataFrame, days: int | None, date_col: str = "date") -> pd.DataFrame:
    """Keep the trailing `days` calendar days (not rows) of `df`."""
    if days is None or df.empty:
        return df
    dates = pd.to_datetime(df[date_col])
    return df[dates >= dates.max() - pd.Timedelta(days=days - 1)]


def calendar_rolling_mean(
    df: pd.DataFrame,
    value_col: str,
    days: int = 7,
    date_col: str = "date",
) -> pd.Series:
    """Average observations in the trailing calendar window, preserving row order.

    Missing dates are not treated as zero. They simply contribute no
    observation, which is appropriate for device data that was not recorded.
    """
    if days < 1:
        raise ValueError("days must be positive")
    if df.empty:
        return pd.Series(index=df.index, dtype=float, name=f"{value_col}_ma{days}")

    work = pd.DataFrame(
        {
            "_date": pd.to_datetime(df[date_col]),
            "_value": df[value_col].to_numpy(),
            "_position": range(len(df)),
        }
    ).sort_values(["_date", "_position"])
    work["_mean"] = work.rolling(f"{days}D", on="_date", min_periods=1)["_value"].mean()
    values = work.sort_values("_position")["_mean"].to_numpy()
    return pd.Series(values, index=df.index, name=f"{value_col}_ma{days}")
