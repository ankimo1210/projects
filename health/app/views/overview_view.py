"""Overview: latest daily cards + 30-day sparklines."""

import pandas as pd
import plotly.express as px
import streamlit as st
from common import clip_days, load_daily
from theme import palette

METRICS = [
    ("steps", "歩数", "{:,.0f}"),
    ("sleep_minutes", "睡眠(分)", "{:,.0f}"),
    ("resting_hr", "安静時心拍", "{:.0f}"),
]


def overview_page() -> None:
    st.title("概要")
    df = load_daily(tuple(m for m, _, _ in METRICS))
    if df.empty:
        st.info("データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, 30).copy()
    df["date"] = pd.to_datetime(df["date"])
    # Each card is an independent single-series sparkline (no shared legend),
    # so every trend uses the same accent hue rather than an identity color.
    accent = palette()["categorical"][0]
    cols = st.columns(len(METRICS))
    for col, (metric, label, fmt) in zip(cols, METRICS, strict=True):
        series = df[["date", metric]].dropna()
        with col:
            if series.empty:
                st.metric(label, "-")
                st.caption("データなし")
                continue
            last = series.iloc[-1]
            delta = None
            if len(series) > 1:
                prev = series.iloc[-2]
                if (last["date"] - prev["date"]).days == 1:
                    delta = last[metric] - prev[metric]
            st.metric(
                label,
                fmt.format(last[metric]),
                delta=fmt.format(delta) if delta is not None else None,
                help="前日比は暦上の前日にデータがある場合のみ表示",
            )
            st.caption(f"{last['date']:%-m/%-d} 時点")
            fig = px.line(df, x="date", y=metric, height=120)
            fig.update_traces(line_color=accent, line_width=2, hovertemplate=None)
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                xaxis_visible=False,
                yaxis_visible=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x",
            )
            st.plotly_chart(fig, width="stretch", key=f"spark_{metric}", theme=None)
