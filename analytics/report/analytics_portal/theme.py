"""Unified minimal-monochrome Plotly theme for the portal.

Applied at render time only (the books keep their committed figure outputs).
The aesthetic: near-achromatic, ONE accent, hairline gridlines, system font,
generous margins. Bright builder colors are remapped so "the important line"
becomes the single accent and everything else turns grayscale.
"""

from __future__ import annotations

import plotly.graph_objects as go

# --- palette (one accent, the rest is ink + grays) ---
INK = "#1d1d1f"
INK_SOFT = "#48484a"
GRAY = "#86868b"
GRAY_2 = "#aeaeb2"
GRAY_3 = "#c7c7cc"
GRID = "#ededf0"
AXIS = "#d2d2d7"
ACCENT = "#2563eb"

FONT = '-apple-system, "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Segoe UI", sans-serif'

# Bright builder hexes -> monochrome + single accent (the "answer" red -> accent).
REMAP = {
    "#d62728": ACCENT,
    "#1f77b4": INK,
    "#2ca02c": GRAY,
    "#ff7f0e": GRAY_2,
    "#9467bd": GRAY_2,
    "#8c564b": GRAY_2,
    "#7f7f7f": GRAY,
    "#c7c7c7": GRAY_3,
    "gray": GRAY_2,
    "grey": GRAY_2,
    "black": INK,
    "k": INK,
}

COLORWAY = [INK, ACCENT, GRAY, GRAY_2, INK_SOFT, GRAY_3]

_axis = {
    "showgrid": True,
    "gridcolor": GRID,
    "gridwidth": 1,
    "zeroline": False,
    "linecolor": AXIS,
    "linewidth": 1,
    "ticks": "outside",
    "tickcolor": AXIS,
    "ticklen": 4,
    "tickfont": {"color": GRAY, "size": 11},
    "title": {"font": {"color": INK_SOFT, "size": 12}},
}

TEMPLATE = go.layout.Template(
    layout={
        "font": {"family": FONT, "size": 13, "color": INK},
        "colorway": COLORWAY,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "title": {"font": {"family": FONT, "size": 14, "color": INK}, "x": 0.0, "xanchor": "left"},
        "margin": {"l": 56, "r": 24, "t": 44, "b": 40},
        "xaxis": _axis,
        "yaxis": _axis,
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": "rgba(0,0,0,0)",
            "font": {"size": 11, "color": INK_SOFT},
        },
        "hoverlabel": {"font": {"family": FONT, "size": 12}},
        "colorscale": {"sequential": "Greys"},
    }
)


def _remap(color):
    if isinstance(color, str):
        return REMAP.get(color, REMAP.get(color.lower(), color))
    return color


def _fix_trace(tr):
    # line color
    if getattr(tr, "line", None) is not None and getattr(tr.line, "color", None) is not None:
        tr.line.color = _remap(tr.line.color)
    # marker color(s) + marker outline + per-marker colorscale
    m = getattr(tr, "marker", None)
    if m is not None:
        col = getattr(m, "color", None)
        if isinstance(col, (list, tuple)):
            m.color = [_remap(c) for c in col]
        elif isinstance(col, str):
            m.color = _remap(col)
        if getattr(m, "colorscale", None) is not None:
            m.colorscale = [[0.0, GRAY_3], [1.0, ACCENT]]
        ml = getattr(m, "line", None)
        if ml is not None and getattr(ml, "color", None) is not None:
            ml.color = _remap(ml.color)
    # filled bands (posterior predictive): keep the alpha, recolor the hue
    fc = getattr(tr, "fillcolor", None)
    if isinstance(fc, str) and "31,119,180" in fc:
        alpha = fc.rstrip(")").split(",")[-1]
        hue = "37,99,235" if float(alpha) >= 0.3 else "134,134,139"
        tr.fillcolor = f"rgba({hue},{alpha})"
    # heatmaps -> a single grayscale ramp
    if tr.type == "heatmap":
        tr.colorscale = "Greys"
    # font on text markers
    if (
        getattr(tr, "textfont", None) is not None
        and getattr(tr.textfont, "color", None) is not None
    ):
        tr.textfont.color = _remap(tr.textfont.color)


def apply_theme(fig):
    """Restyle a figure into the unified minimal-monochrome theme."""
    fig.update_layout(template=TEMPLATE, colorway=COLORWAY)
    # Initial traces AND every animation frame's traces carry their own colors.
    fig.for_each_trace(_fix_trace)
    for fr in fig.frames or ():
        for tr in fr.data or ():
            _fix_trace(tr)
    # slider readout in muted ink
    for sl in fig.layout.sliders or ():
        sl.currentvalue.font = {"color": GRAY, "size": 11}
        sl.font = {"color": GRAY, "size": 10}
    return fig
