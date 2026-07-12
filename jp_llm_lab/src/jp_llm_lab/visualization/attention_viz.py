"""Attention visualizations (Milestone-1 subset of spec §9)."""

from __future__ import annotations

import plotly.graph_objects as go
import torch
from plotly.subplots import make_subplots

from .style import base_layout


def attention_entropy(weights: torch.Tensor) -> torch.Tensor:
    """Mean attention entropy per head: H = -Σ_j a_tj log a_tj, averaged over t.

    weights: [B,H,T,T] (rows already sum to 1 over the causal prefix).
    Note: row t has only t+1 admissible keys, so its max entropy is log(t+1);
    early positions are inherently low-entropy. We average anyway and flag the
    caveat where the figure is shown.
    """
    w = weights.float().clamp(min=1e-12)
    h = -(w * w.log()).sum(dim=-1)  # [B,H,T] (masked zeros contribute 0)
    return h.mean(dim=(0, 2))  # [H]


def attention_heatmap_grid(
    weights: torch.Tensor, tokens: list[str], title: str, max_heads: int = 4
) -> go.Figure:
    """One heatmap per head for a single sequence. weights: [H,T,T]."""
    H = min(weights.shape[0], max_heads)
    T = weights.shape[-1]
    labels = [f"{i}:{t}" for i, t in enumerate(tokens[:T])]
    fig = make_subplots(rows=1, cols=H, subplot_titles=[f"head {h}" for h in range(H)],
                        horizontal_spacing=0.03)
    for h in range(H):
        fig.add_trace(
            go.Heatmap(
                z=weights[h].tolist(), x=labels, y=labels, colorscale="Blues",
                zmin=0, zmax=1, showscale=(h == H - 1),
                hovertemplate="query %{y}<br>key %{x}<br>weight %{z:.3f}<extra></extra>",
            ),
            row=1, col=h + 1,
        )
    fig.update_layout(height=380, template="plotly_white", title=title,
                      margin=dict(l=60, r=30, t=80, b=50))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(showticklabels=(T <= 24))
    return fig


def entropy_comparison_figure(
    entropies_by_label: dict[str, torch.Tensor], n_layers: int, n_heads: int
) -> go.Figure:
    """entropies_by_label: {"init": [L,H] tensor, "trained": [L,H] tensor}."""
    fig = go.Figure()
    for label, ent in entropies_by_label.items():
        flat = ent.flatten().tolist()
        names = [f"L{layer}H{h}" for layer in range(n_layers) for h in range(n_heads)]
        fig.add_trace(go.Bar(x=names, y=flat, name=label))
    fig.update_layout(barmode="group")
    return base_layout(fig, "Attention entropy per layer/head (mean over positions)",
                       "layer/head", "entropy (nats)")
