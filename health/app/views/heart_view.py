"""Heart: resting HR / HRV trends, intraday viewer."""

from datetime import date

import plotly.express as px
import streamlit as st
from common import get_store

# dataviz skill palette (references/palette.md) — one series per chart -> slot 1 (blue).
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
MUTED_TEXT = "#898781"
ACCENT = "#2a78d6"


def _style(fig):
    fig.update_layout(
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font_color="#0b0b0b",
        margin=dict(t=30, l=10, r=10, b=10),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    return fig


def heart_page() -> None:
    st.title("心拍")
    store = get_store()
    df = store.daily_frame(["resting_hr", "hrv_rmssd"])
    if df.empty:
        st.info("心拍データがありません。")
        return

    st.subheader("安静時心拍（長期トレンド）")
    fig = px.line(
        df.dropna(subset=["resting_hr"]),
        x="date",
        y="resting_hr",
        labels={"date": "日付", "resting_hr": "bpm"},
    )
    fig.update_traces(line_color=ACCENT, line_width=2)
    st.plotly_chart(_style(fig), use_container_width=True, theme=None)

    st.subheader("HRV (RMSSD)")
    hrv = df.dropna(subset=["hrv_rmssd"])
    if hrv.empty:
        st.caption("HRV データなし（デバイス非対応の可能性）")
    else:
        fig = px.line(hrv, x="date", y="hrv_rmssd", labels={"date": "日付", "hrv_rmssd": "ms"})
        fig.update_traces(line_color=ACCENT, line_width=2)
        st.plotly_chart(_style(fig), use_container_width=True, theme=None)

    st.subheader("分単位心拍ビューア")
    day = st.date_input("日付", value=date.today(), key="hr_day")
    intra = store.intraday_frame("hr", day)
    if intra.empty:
        st.caption("この日の intraday データはありません（直近30日のみ取得）。")
    else:
        fig = px.line(intra, x="ts", y="value", labels={"value": "bpm", "ts": "時刻"})
        fig.update_traces(line_color=ACCENT, line_width=2)
        st.plotly_chart(_style(fig), use_container_width=True, theme=None)
