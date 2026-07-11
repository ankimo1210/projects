"""Model-comparison figures (spec §17) — ablation chain and size scaling."""

from __future__ import annotations

import plotly.graph_objects as go

from .style import base_layout


def ablation_val_loss_figure(summary: dict) -> go.Figure:
    """val loss mean ± std across the Classical→Modern chain, with a seed-noise band."""
    chain = summary["chain"]
    res = summary["results"]
    means = [res[c]["val_loss_mean"] for c in chain]
    stds = [res[c]["val_loss_std"] for c in chain]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chain, y=means,
            error_y=dict(type="data", array=stds, visible=True),
            mode="lines+markers", line=dict(color="#1f77b4"), name="val loss (3 seeds)",
        )
    )
    # reference band: ± mean seed std around the classical baseline
    base = means[0]
    band = sum(stds) / len(stds)
    fig.add_hrect(y0=base - band, y1=base + band, fillcolor="#7f7f7f", opacity=0.12, line_width=0,
                  annotation_text="±1σ seed-noise band (baseline)")
    return base_layout(fig, "Classical→Modern ablation: val loss (each step flips ONE switch)",
                       "architecture step", "validation loss (nats/token)")


def ablation_table_rows(summary: dict) -> list[dict]:
    res = summary["results"]
    base = res[summary["chain"][0]]["val_loss_mean"]
    rows = []
    prev = base
    for c in summary["chain"]:
        r = res[c]
        rows.append(
            {
                "step": c,
                "n_params": r["n_params"],
                "val_loss": round(r["val_loss_mean"], 4),
                "std": round(r["val_loss_std"], 4),
                "delta_vs_prev": round(r["val_loss_mean"] - prev, 4),
                "delta_vs_base": round(r["val_loss_mean"] - base, 4),
                "top1_conf": round(r["top1_conf_mean"], 4),
            }
        )
        prev = r["val_loss_mean"]
    return rows


def size_scaling_figure(points: list[dict]) -> go.Figure:
    """val loss vs params (log-x), for the S/M/L scaling comparison."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[p["n_params"] for p in points], y=[p["val_loss"] for p in points],
            mode="lines+markers+text", text=[p["name"] for p in points], textposition="top center",
            line=dict(color="#2ca02c"),
        )
    )
    fig.update_xaxes(type="log")
    return base_layout(fig, "Scaling: validation loss vs parameters (matched tokens)",
                       "parameters (log)", "validation loss (nats/token)")
