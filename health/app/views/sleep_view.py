"""Sleep: stage composition, duration trend, bed/wake scatter."""
import pandas as pd
import plotly.express as px
import streamlit as st

from common import get_store

STAGES = [("minutes_deep", "深い"), ("minutes_rem", "REM"),
          ("minutes_light", "浅い"), ("minutes_wake", "覚醒")]

# dataviz skill palette (references/palette.md) — fixed categorical hue order,
# assigned in sequence (never cycled) to each chart's series.
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
MUTED_TEXT = "#898781"
CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100",
               "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
STAGE_COLORS = {label: CATEGORICAL[i] for i, (_, label) in enumerate(STAGES)}


def _style(fig):
    """Common chart chrome: surface bg, hairline recessive gridlines, muted ink."""
    fig.update_layout(plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font_color="#0b0b0b",
                       legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(t=30, l=10, r=10, b=10),
                       hovermode="x unified")
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    return fig


def sleep_page() -> None:
    st.title("睡眠")
    sf = get_store().sleep_frame()
    sf = sf[sf["is_main"]].copy()
    if sf.empty:
        st.info("睡眠データがありません。")
        return
    days = st.slider("表示日数", 14, 180, 60, key="sleep_days")
    sf = sf.tail(days)

    long = sf.melt(id_vars=["date"], value_vars=[c for c, _ in STAGES],
                   var_name="stage", value_name="minutes")
    long["stage"] = long["stage"].map(dict(STAGES))
    st.subheader("ステージ構成")
    fig = px.bar(long, x="date", y="minutes", color="stage",
                color_discrete_map=STAGE_COLORS,
                labels={"minutes": "分", "date": "日付", "stage": "ステージ"})
    # surface gap between stacked segments (mark spec) instead of a border stroke
    fig.update_traces(marker_line_color=SURFACE, marker_line_width=2)
    st.plotly_chart(_style(fig), use_container_width=True, theme=None)

    st.subheader("睡眠時間トレンド（7日移動平均）")
    trend = sf[["date", "minutes_asleep"]].copy()
    trend["ma7"] = trend["minutes_asleep"].rolling(7).mean()
    trend = trend.rename(columns={"minutes_asleep": "実績", "ma7": "7日移動平均"})
    fig = px.line(trend, x="date", y=["実績", "7日移動平均"],
                 color_discrete_sequence=CATEGORICAL,
                 labels={"date": "日付", "value": "分", "variable": ""})
    fig.update_traces(line_width=2)
    st.plotly_chart(_style(fig), use_container_width=True, theme=None)

    st.subheader("就寝・起床時刻")
    tt = pd.DataFrame({
        "date": sf["date"],
        "就寝": pd.to_datetime(sf["start_ts"]).dt.hour + pd.to_datetime(sf["start_ts"]).dt.minute / 60,
        "起床": pd.to_datetime(sf["end_ts"]).dt.hour + pd.to_datetime(sf["end_ts"]).dt.minute / 60,
    }).melt(id_vars="date", var_name="event", value_name="hour")
    fig = px.scatter(tt, x="date", y="hour", color="event",
                     color_discrete_map={"就寝": CATEGORICAL[0], "起床": CATEGORICAL[1]},
                     labels={"date": "日付", "hour": "時刻", "event": ""})
    fig.update_traces(marker=dict(size=8, line=dict(width=2, color=SURFACE)))
    st.plotly_chart(_style(fig), use_container_width=True, theme=None)
