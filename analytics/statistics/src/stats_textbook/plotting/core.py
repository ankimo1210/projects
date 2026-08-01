"""Shared Plotly scaffolding.

Every figure in this book must animate inside a *static* HTML page, so the
frames and slider steps are baked into the figure object rather than driven
by a live kernel. ipywidgets is a convenience layer on top (see ``widgets``),
never a requirement.
"""

from __future__ import annotations

from collections.abc import Sequence

import plotly.graph_objects as go

__all__ = ["apply_defaults", "curve_slider", "frame_slider"]

Curve = tuple[str, Sequence[float], str | None]
Frame = tuple[str, list[Curve]]


def apply_defaults(
    fig: go.Figure,
    title: str | None = None,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
) -> go.Figure:
    """One house style for size, margins, and axis titles."""
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        width=760,
        height=460,
        margin={"l": 60, "r": 30, "t": 60 if title else 30, "b": 50},
        template="plotly_white",
    )
    return fig


def frame_slider(frames: list[go.Frame], slider_name: str) -> go.Figure:
    """Assemble pre-built frames into a figure with a slider over them.

    Every animated figure in the book funnels through here so the slider
    wiring exists once. Callers build the frames -- what varies between
    figures is the marks, not the animation machinery.
    """
    fig = go.Figure(data=frames[0].data, frames=frames)
    fig.update_layout(
        sliders=[
            {
                "steps": [
                    {
                        "args": [
                            [f.name],
                            {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
                        ],
                        "label": f.name,
                        "method": "animate",
                    }
                    for f in frames
                ],
                "currentvalue": {"prefix": f"{slider_name} = "},
            }
        ]
    )
    return fig


def _traces(x: Sequence[float], curves: list[Curve]) -> list[go.Scatter]:
    return [
        go.Scatter(
            x=list(x),
            y=list(y),
            mode="lines",
            name=name,
            line={"dash": dash} if dash else None,
        )
        for name, y, dash in curves
    ]


def curve_slider(
    x: Sequence[float],
    frames: list[Frame],
    slider_name: str = "step",
    title: str | None = None,
    yaxis_title: str | None = None,
) -> go.Figure:
    """A line plot with a slider stepping through ``frames``.

    ``frames`` is a list of ``(label, curves)``; each ``curves`` entry is
    ``(name, y, dash_or_None)`` over the shared ``x`` grid.

    Part I's figures are bars and histograms and so build their frames
    directly; this line-oriented wrapper is what Plan 2's likelihood and
    power curves use.
    """
    built = [go.Frame(data=_traces(x, curves), name=str(lab)) for lab, curves in frames]
    return apply_defaults(frame_slider(built, slider_name), title=title, yaxis_title=yaxis_title)
