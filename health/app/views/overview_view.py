"""Overview: today's cards + 30-day sparklines."""

import plotly.express as px
import streamlit as st
from common import get_store

METRICS = [
    ("steps", "歩数", "{:,.0f}"),
    ("sleep_minutes", "睡眠(分)", "{:,.0f}"),
    ("resting_hr", "安静時心拍", "{:.0f}"),
]

# dataviz skill palette (references/palette.md) — categorical slot 1 (blue).
# Each card is an independent single-series sparkline (no shared legend needed),
# so every trend uses the same accent hue rather than a distinct identity color.
ACCENT = "#2a78d6"


def overview_page() -> None:
    st.title("概要")
    df = get_store().daily_frame([m for m, _, _ in METRICS]).tail(30)
    if df.empty:
        st.info("データがありません。まず「同期」ページで同期してください。")
        return
    cols = st.columns(len(METRICS))
    for col, (metric, label, fmt) in zip(cols, METRICS, strict=True):
        series = df[metric].dropna()
        with col:
            if series.empty:
                st.metric(label, "-")
                continue
            delta = series.iloc[-1] - series.iloc[-2] if len(series) > 1 else None
            st.metric(
                label,
                fmt.format(series.iloc[-1]),
                delta=fmt.format(delta) if delta is not None else None,
            )
            fig = px.line(df, x="date", y=metric, height=120)
            fig.update_traces(line_color=ACCENT, line_width=2, hovertemplate=None)
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                xaxis_visible=False,
                yaxis_visible=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x",
            )
            st.plotly_chart(fig, use_container_width=True, key=f"spark_{metric}", theme=None)
