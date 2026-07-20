"""Body: weight, SpO2, skin temp, breathing rate."""
import plotly.express as px
import streamlit as st

from common import get_store

# Each group shares one y-axis, so metrics of different units/scale are never
# combined on the same chart (dataviz anti-pattern: mismatched-scale series on
# one axis flattens the smaller one). weight_kg and fat_pct — different units —
# are split into their own single-metric panels instead of the brief's shared
# "体重・体脂肪" panel; SpO2's three sub-metrics share one % scale so stay combined.
PANELS = [(["weight_kg"], "体重"),
          (["fat_pct"], "体脂肪率"),
          (["spo2_avg", "spo2_min", "spo2_max"], "SpO2"),
          (["temp_skin_relative"], "皮膚温（基準比）"),
          (["breathing_rate"], "呼吸数")]

JP_LABELS = {"weight_kg": "kg", "fat_pct": "%", "spo2_avg": "平均", "spo2_min": "最小",
             "spo2_max": "最大", "temp_skin_relative": "基準比", "breathing_rate": "回/分"}

# dataviz skill palette (references/palette.md) — fixed categorical hue order.
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
MUTED_TEXT = "#898781"
CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100",
               "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
# For thin 2px lines, skip the palette's WARN-contrast slots (magenta #e87ba4,
# yellow #eda100, aqua #1baf7a — all sub-3:1 on the light surface per
# scripts/validate_palette.js); thin marks are exactly where low contrast is
# risky, unlike thick fills where the palette's own WARN is tolerable behind
# the legend. Relative fixed order is preserved (slot 1, then 2, then 6),
# just skipping the WARN slots rather than slicing the first N.
LINE_SAFE = [CATEGORICAL[0], CATEGORICAL[1], CATEGORICAL[5]]


def _style(fig):
    fig.update_layout(plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font_color="#0b0b0b",
                       legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(t=30, l=10, r=10, b=10),
                       hovermode="x unified")
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    return fig


def body_page() -> None:
    st.title("身体")
    df = get_store().daily_frame(sorted({m for ms, _ in PANELS for m in ms}))
    if df.empty:
        st.info("身体データがありません。")
        return
    for metrics, label in PANELS:
        sub = df[["date", *metrics]].dropna(how="all", subset=metrics)
        st.subheader(label)
        if sub.empty:
            st.caption("データなし（デバイス非対応の可能性）")
            continue
        if len(metrics) == 1:
            m = metrics[0]
            fig = px.line(sub, x="date", y=m, labels={"date": "日付", m: JP_LABELS[m]})
            fig.update_traces(line_color=CATEGORICAL[0], line_width=2)
        else:
            renamed = sub.rename(columns={m: JP_LABELS[m] for m in metrics})
            cols = [JP_LABELS[m] for m in metrics]
            fig = px.line(renamed, x="date", y=cols, color_discrete_sequence=LINE_SAFE,
                         labels={"date": "日付", "value": "%", "variable": ""})
            fig.update_traces(line_width=2)
        st.plotly_chart(_style(fig), use_container_width=True, theme=None)
