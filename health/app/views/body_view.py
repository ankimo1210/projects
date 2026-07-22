"""Body: weight, body fat, SpO2 (avg/lower/upper), skin temp, breathing rate."""

import plotly.express as px
import streamlit as st
from common import clip_days, load_daily, period_days
from theme import palette, style

# Each group shares one y-axis, so metrics of different units/scale are never
# combined on the same chart (dataviz anti-pattern: mismatched-scale series on
# one axis flattens the smaller one). weight_kg and fat_pct — different units —
# stay in their own single-metric panels; SpO2's three sub-metrics share one
# % scale so they stay combined.
PANELS = [
    (["weight_kg"], "体重"),
    (["fat_pct"], "体脂肪率"),
    (["spo2_avg", "spo2_lower_bound", "spo2_upper_bound"], "SpO2"),
    (["temp_skin_relative"], "皮膚温（基準比）"),
    (["breathing_rate"], "呼吸数"),
]

JP_LABELS = {
    "weight_kg": "kg",
    "fat_pct": "%",
    "spo2_avg": "平均",
    "spo2_lower_bound": "下限",
    "spo2_upper_bound": "上限",
    "temp_skin_relative": "基準比",
    "breathing_rate": "回/分",
}


def body_page() -> None:
    st.title("身体")
    p = palette()
    df = load_daily(tuple(sorted({m for ms, _ in PANELS for m in ms})))
    if df.empty:
        st.info("身体データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days())
    for metrics, label in PANELS:
        sub = df[["date", *metrics]].dropna(how="all", subset=metrics)
        st.subheader(label)
        if sub.empty:
            st.caption("データなし（デバイス非対応の可能性）")
            continue
        if len(metrics) == 1:
            m = metrics[0]
            fig = px.line(sub, x="date", y=m, labels={"date": "日付", m: JP_LABELS[m]})
            fig.update_traces(line_color=p["categorical"][0], line_width=2)
        else:
            renamed = sub.rename(columns={m: JP_LABELS[m] for m in metrics})
            fig = px.line(
                renamed,
                x="date",
                y=[JP_LABELS[m] for m in metrics],
                color_discrete_sequence=p["line_safe"],
                labels={"date": "日付", "value": "%", "variable": ""},
            )
            fig.update_traces(line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)
