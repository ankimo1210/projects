"""Alert Monitor: 条件ベースアラート一覧。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yaml
from market_viz.analytics.signals import build_alert_df
from market_viz.storage.duckdb_client import DuckDBClient

with open("src/config/settings.yaml") as f:
    _cfg = yaml.safe_load(f)

DB_PATH = _cfg["data"]["db_path"]
ALERT_CFG = _cfg.get("alerts", {})


@st.cache_resource
def get_db() -> DuckDBClient:
    db = DuckDBClient(DB_PATH)
    db.connect()
    return db


@st.cache_data(ttl=300)
def load_prices_all(start: str) -> pd.DataFrame:
    db = get_db()
    with open("src/config/instruments.yaml") as f:
        cfg = yaml.safe_load(f)
    tickers = [i["ticker"] for g in cfg["instruments"].values() for i in g]
    return db.get_prices(tickers, frequency="1d", start=start)


st.set_page_config(layout="wide")
st.title("🔔 Alert Monitor")

# ----------------------------------------------------------------
# Controls
# ----------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    period_days = st.selectbox("評価期間", [90, 180, 365], index=1)
with col2:
    zscore_thresh = st.slider(
        "Z-Score 閾値", 1.0, 3.0, float(ALERT_CFG.get("zscore_alert_threshold", 2.0)), step=0.1
    )
with col3:
    ret_thresh = st.slider(
        "1日リターン 閾値 (%)",
        1.0,
        10.0,
        float(ALERT_CFG.get("return_threshold_pct", 5.0)),
        step=0.5,
    )
with col4:
    vol_mult = st.slider(
        "ボラ急騰 倍率", 1.0, 3.0, float(ALERT_CFG.get("vol_spike_threshold", 1.5)), step=0.1
    )

# ----------------------------------------------------------------
# Generate alerts
# ----------------------------------------------------------------
start_str = (date.today() - timedelta(days=period_days)).isoformat()
prices_df = load_prices_all(start_str)

if prices_df.empty:
    st.warning("データがありません。データ更新を実行してください。")
    st.stop()

if st.button("🔄 アラート再計算", type="primary"):
    st.cache_data.clear()

alerts_df = build_alert_df(
    prices_df,
    vol_spike_mult=vol_mult,
    zscore_thresh=zscore_thresh,
    return_thresh_pct=ret_thresh,
)

# ----------------------------------------------------------------
# Summary
# ----------------------------------------------------------------
if alerts_df.empty:
    st.success("現在アクティブなアラートはありません。")
    st.stop()

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("総アラート数", len(alerts_df))
with col_s2:
    n_ret = (
        (alerts_df["condition_type"] == "return_1d").sum()
        if "condition_type" in alerts_df.columns
        else 0
    )
    st.metric("リターン系", n_ret)
with col_s3:
    n_z = (
        (alerts_df["condition_type"] == "zscore_20d").sum()
        if "condition_type" in alerts_df.columns
        else 0
    )
    st.metric("Z-Score系", n_z)
with col_s4:
    n_v = (
        (alerts_df["condition_type"] == "vol_spike").sum()
        if "condition_type" in alerts_df.columns
        else 0
    )
    st.metric("ボラ急騰", n_v)

st.markdown("---")

# ----------------------------------------------------------------
# Alert table
# ----------------------------------------------------------------
COND_LABEL = {
    "return_1d": "📈 リターン1D",
    "zscore_20d": "📊 Z-Score",
    "vol_spike": "⚡ ボラ急騰",
}

display_df = alerts_df.copy()
if "condition_type" in display_df.columns:
    display_df["条件"] = display_df["condition_type"].map(lambda x: COND_LABEL.get(x, x))

cols_show = ["ticker", "条件", "current_value", "threshold", "message", "triggered_at"]
cols_show = [c for c in cols_show if c in display_df.columns]
display_df = display_df[cols_show].rename(
    columns={
        "ticker": "銘柄",
        "current_value": "現在値",
        "threshold": "閾値",
        "message": "メッセージ",
        "triggered_at": "発生時刻",
    }
)


def _alert_style(val):
    if isinstance(val, str):
        if "リターン" in val:
            return "color: #ff9800"
        if "Z-Score" in val:
            return "color: #42a5f5"
        if "ボラ" in val:
            return "color: #ef5350"
    return ""


styled = display_df.style.applymap(_alert_style, subset=["条件"])
if "現在値" in display_df.columns:
    styled = styled.format({"現在値": "{:.3f}", "閾値": "{:.3f}"}, na_rep="-")

st.dataframe(styled, use_container_width=True, height=400)

# ----------------------------------------------------------------
# Type breakdown chart
# ----------------------------------------------------------------
if "condition_type" in alerts_df.columns:
    st.markdown("---")
    st.subheader("アラート種別")
    breakdown = alerts_df["condition_type"].value_counts().rename(index=COND_LABEL)
    st.bar_chart(breakdown)
