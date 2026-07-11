"""Shared plot style: one color per concept, used consistently everywhere
(spec §24 — train/val, explicit/SDPA, greedy/sampled never swap colors)."""

from __future__ import annotations

import plotly.graph_objects as go

COLORS = {
    "train": "#1f77b4",  # blue
    "val": "#d62728",  # red
    "explicit": "#9467bd",  # purple
    "sdpa": "#2ca02c",  # green
    "count": "#7f7f7f",  # gray (closed-form reference)
    "neural": "#ff7f0e",  # orange
    "greedy": "#1f77b4",
    "sampled": "#ff7f0e",
    "reference": "#7f7f7f",
    "accent": "#e377c2",
}

GROUP_COLORS = {
    "token_emb": "#1f77b4",
    "pos_emb": "#aec7e8",
    "attn_qkv": "#2ca02c",
    "attn_proj": "#98df8a",
    "mlp": "#ff7f0e",
    "norm": "#c5b0d5",
    "lm_head": "#d62728",
}


def base_layout(fig: go.Figure, title: str, xtitle: str, ytitle: str, height: int = 420) -> go.Figure:
    fig.update_layout(
        title=title,
        xaxis_title=xtitle,
        yaxis_title=ytitle,
        height=height,
        template="plotly_white",
        margin=dict(l=60, r=30, t=60, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=12),
    )
    return fig
