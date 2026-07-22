"""Heart: resting HR / HRV (avg + deep sleep) trends, intraday HR viewer."""

from datetime import date

import plotly.express as px
import streamlit as st
from common import clip_days, load_daily, load_intraday, period_days
from theme import palette, style


def heart_page() -> None:
    st.title("心拍")
    p = palette()
    df = load_daily(("resting_hr", "hrv_rmssd", "hrv_deep_rmssd"))
    if df.empty:
        st.info("心拍データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days())

    st.subheader("安静時心拍")
    rh = df.dropna(subset=["resting_hr"])
    if rh.empty:
        st.caption("データなし（デバイス非対応の可能性）")
    else:
        fig = px.line(rh, x="date", y="resting_hr", labels={"date": "日付", "resting_hr": "bpm"})
        fig.update_traces(line_color=p["categorical"][0], line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("HRV (RMSSD)")
    hrv = df.dropna(subset=["hrv_rmssd", "hrv_deep_rmssd"], how="all")
    if hrv.empty:
        st.caption("HRV データなし（デバイス非対応の可能性）")
    else:
        renamed = hrv.rename(columns={"hrv_rmssd": "平均", "hrv_deep_rmssd": "深い睡眠時"})
        fig = px.line(
            renamed,
            x="date",
            y=["平均", "深い睡眠時"],
            color_discrete_sequence=p["line_safe"],
            labels={"date": "日付", "value": "ms", "variable": ""},
        )
        fig.update_traces(line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("分単位心拍ビューア")
    day = st.date_input("日付", value=date.today(), key="hr_day")
    intra = load_intraday("hr", day)
    if intra.empty:
        st.caption("この日の intraday データはありません（直近30日のみ取得）。")
    else:
        fig = px.line(intra, x="ts", y="value", labels={"value": "bpm", "ts": "時刻"})
        fig.update_traces(line_color=p["categorical"][0], line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)
