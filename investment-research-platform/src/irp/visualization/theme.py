"""A restrained, consistent Plotly theme (clean, near-monochrome).

One ``style()`` call gives every figure the same look so a report reads as one
document, not a pile of defaults.
"""

from __future__ import annotations

import plotly.graph_objects as go

#: ordered colorway — ink first, then a calm categorical palette
COLORWAY = ["#111111", "#4C78A8", "#E45756", "#54A24B", "#B279A2", "#EECA3B", "#72B7B2"]
TEMPLATE = "plotly_white"
FONT = "Inter, system-ui, -apple-system, Segoe UI, sans-serif"
GRID = "rgba(0,0,0,0.06)"


def style(fig: go.Figure, title: str | None = None, *, height: int = 420) -> go.Figure:
    fig.update_layout(
        template=TEMPLATE,
        colorway=COLORWAY,
        title=title,
        height=height,
        margin={"l": 60, "r": 30, "t": 60 if title else 30, "b": 50},
        font={"family": FONT, "size": 13, "color": "#111"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return fig
