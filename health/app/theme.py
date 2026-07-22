"""Shared chart chrome: dataviz palette (light + dark) and Plotly styling.

Palette source: dataviz skill references/palette.md (July 2026 ordering).
Light and dark are both selected steps of the same hues — never an automatic
flip. The categorical slot order is the CVD-safety mechanism: assign hues in
fixed order, never cycled.
"""

import streamlit as st

_SEQ_LIGHT = [
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
]

LIGHT = {
    "surface": "#fcfcfb",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "muted": "#898781",
    "ink": "#0b0b0b",
    "categorical": [
        "#2a78d6",
        "#eb6834",
        "#1baf7a",
        "#eda100",
        "#e87ba4",
        "#008300",
        "#4a3aa7",
        "#e34948",
    ],
    # Thin 2px lines skip the sub-3:1 slots on the light surface (aqua,
    # yellow, magenta) — the palette's relief rule; fixed order preserved.
    "line_safe": ["#2a78d6", "#eb6834", "#008300"],
    "sequential": _SEQ_LIGHT,
}

DARK = {
    "surface": "#1a1a19",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "muted": "#898781",
    "ink": "#ffffff",
    "categorical": [
        "#3987e5",
        "#d95926",
        "#199e70",
        "#c98500",
        "#d55181",
        "#008300",
        "#9085e9",
        "#e66767",
    ],
    # Dark steps are >= 3:1 on the dark surface; keep the same leading hues
    # as light mode so series identity survives a theme switch.
    "line_safe": ["#3987e5", "#d95926", "#008300"],
    "sequential": list(reversed(_SEQ_LIGHT)),  # low=dark, high=light on dark surface
}


def palette() -> dict:
    """Palette for the viewer's current Streamlit theme (light by default)."""
    theme = getattr(st.context, "theme", None)
    dark = theme is not None and getattr(theme, "type", "light") == "dark"
    return DARK if dark else LIGHT


def style(fig, p: dict | None = None):
    """Common chart chrome: surface bg, hairline recessive grid, muted ink."""
    p = p or palette()
    fig.update_layout(
        plot_bgcolor=p["surface"],
        paper_bgcolor=p["surface"],
        font_color=p["ink"],
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=30, l=10, r=10, b=10),
        hovermode="x unified",
    )
    fig.update_xaxes(
        gridcolor=p["grid"], linecolor=p["axis"], tickfont_color=p["muted"], zeroline=False
    )
    fig.update_yaxes(
        gridcolor=p["grid"], linecolor=p["axis"], tickfont_color=p["muted"], zeroline=False
    )
    return fig
