"""Parameter-count and benchmark figures."""

from __future__ import annotations

import plotly.graph_objects as go

from .style import COLORS, GROUP_COLORS, base_layout


def param_breakdown_figure(breakdown: dict) -> go.Figure:
    groups = breakdown["groups"]
    names = sorted(groups, key=groups.get, reverse=True)
    total = breakdown["total"]
    fig = go.Figure(
        go.Bar(
            x=names,
            y=[groups[n] for n in names],
            marker_color=[GROUP_COLORS.get(n, "#333") for n in names],
            text=[f"{groups[n]/total:.1%}" for n in names],
            textposition="outside",
        )
    )
    tied = " (lm_head tied to token_emb → 0 extra params)" if breakdown.get("tied") else ""
    return base_layout(
        fig, f"Parameter breakdown — total {total:,}{tied}", "component", "parameters"
    )


def attn_bench_figure(bench: dict) -> go.Figure:
    """Explicit vs SDPA median step time by (dtype, T)."""
    results = bench["results"]
    fig = go.Figure()
    for impl in ("explicit", "sdpa"):
        rows = [r for r in results if r["impl"] == impl]
        fig.add_trace(
            go.Bar(
                x=[f'{r["dtype"]} T={r["T"]}' for r in rows],
                y=[r["median_ms"] for r in rows],
                name=impl,
                marker_color=COLORS[impl],
                text=[f'{r["median_ms"]:.1f}ms' for r in rows],
            )
        )
    fig.update_layout(barmode="group")
    return base_layout(
        fig,
        "Attention forward+backward median time — explicit vs SDPA (B=32, d=128, RTX 5080)",
        "dtype / sequence length",
        "median ms (lower is better)",
    )
