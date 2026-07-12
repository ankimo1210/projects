"""Training-dynamics figures built from a run's metrics.jsonl records."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .style import COLORS, GROUP_COLORS, base_layout


def _split(records: list[dict]) -> tuple[list[dict], list[dict]]:
    return (
        [r for r in records if r["type"] == "train"],
        [r for r in records if r["type"] == "eval"],
    )


def loss_curves_figure(records: list[dict]) -> go.Figure:
    """Train/val loss with x-axis switchable between steps / tokens / time.

    The per-step train loss (thin) is the noisy minibatch loss; the eval
    curves (markers) are fixed-batch estimates — smoother and comparable
    across the run.
    """
    trains, evals = _split(records)
    axes = {
        "step": ("step", "optimizer step"),
        "tokens": ("tokens_seen", "tokens seen"),
        "time": ("elapsed_sec", "wall-clock sec"),
    }

    # older eval records lack elapsed_sec — interpolate from train records
    t_steps = [r["step"] for r in trains]
    t_elapsed = [r["elapsed_sec"] for r in trains]

    def field_of(r: dict, field: str) -> float:
        if field in r:
            return r[field]
        assert field == "elapsed_sec"
        import bisect

        i = min(bisect.bisect_left(t_steps, r["step"]), len(t_steps) - 1)
        return t_elapsed[i]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[r["step"] for r in trains], y=[r["loss"] for r in trains],
            name="train (per-step minibatch)", mode="lines",
            line=dict(color=COLORS["train"], width=1), opacity=0.45,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[r["step"] for r in evals], y=[r["train_eval"]["loss"] for r in evals],
            name="train (fixed eval batches)", mode="lines+markers", line=dict(color=COLORS["train"]),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[r["step"] for r in evals], y=[r["val_eval"]["loss"] for r in evals],
            name="validation", mode="lines+markers", line=dict(color=COLORS["val"]),
        )
    )
    buttons = []
    for key, (field, label) in axes.items():
        xs = [
            [field_of(r, field) for r in trains],
            [field_of(r, field) for r in evals],
            [field_of(r, field) for r in evals],
        ]
        buttons.append(
            dict(label=key, method="update", args=[{"x": xs}, {"xaxis": {"title": {"text": label}}}])
        )
    fig.update_layout(
        updatemenus=[dict(type="buttons", direction="right", x=0.0, y=1.18, buttons=buttons)]
    )
    return base_layout(fig, "Loss curves (train vs validation)", "optimizer step", "cross-entropy loss (nats/token)")


def lr_grad_figure(records: list[dict], grad_clip: float) -> go.Figure:
    trains, _ = _split(records)
    steps = [r["step"] for r in trains]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("learning rate", "gradient norm (pre-clip)"))
    fig.add_trace(go.Scatter(x=steps, y=[r["lr"] for r in trains], name="lr", line=dict(color=COLORS["accent"])), row=1, col=1)
    fig.add_trace(go.Scatter(x=steps, y=[r["grad_norm"] for r in trains], name="‖g‖₂", line=dict(color=COLORS["train"])), row=2, col=1)
    fig.add_hline(y=grad_clip, line_dash="dash", line_color=COLORS["reference"], row=2, col=1,
                  annotation_text=f"clip threshold {grad_clip}")
    fig.update_layout(height=520, template="plotly_white", title="LR schedule and gradient norm",
                      margin=dict(l=60, r=30, t=60, b=50), showlegend=False)
    fig.update_xaxes(title_text="optimizer step", row=2, col=1)
    return fig


def update_ratio_figure(records: list[dict]) -> go.Figure:
    trains, _ = _split(records)
    with_ratio = [r for r in trains if "update_ratios" in r]
    fig = go.Figure()
    groups = sorted({g for r in with_ratio for g in r["update_ratios"]})
    for g in groups:
        fig.add_trace(
            go.Scatter(
                x=[r["step"] for r in with_ratio],
                y=[r["update_ratios"].get(g) for r in with_ratio],
                name=g, mode="lines+markers", line=dict(color=GROUP_COLORS.get(g)),
            )
        )
    fig.add_hline(y=1e-3, line_dash="dot", line_color=COLORS["reference"],
                  annotation_text="~1e-3 (healthy AdamW rule of thumb)")
    fig.update_yaxes(type="log")
    return base_layout(fig, "Update-to-weight ratio ‖ΔW‖/‖W‖ per parameter group", "optimizer step", "ratio (log)")


def grad_norm_by_group_figure(records: list[dict]) -> go.Figure:
    trains, _ = _split(records)
    trains = [r for r in trains if r.get("grad_norms")]
    fig = go.Figure()
    groups = sorted({g for r in trains for g in r["grad_norms"]})
    for g in groups:
        fig.add_trace(
            go.Scatter(
                x=[r["step"] for r in trains], y=[r["grad_norms"].get(g) for r in trains],
                name=g, mode="lines", line=dict(color=GROUP_COLORS.get(g)),
            )
        )
    fig.update_yaxes(type="log")
    return base_layout(fig, "Gradient norm per parameter group", "optimizer step", "‖g‖₂ (log)")


def activation_rms_heatmap(records: list[dict]) -> go.Figure:
    """Residual-stream RMS: checkpoint (x) × observation point (y)."""
    _, evals = _split(records)
    points = [p for p in evals[0]["activation_stats"] if p.endswith(".resid") or p in ("tok_emb", "ln_f")]
    z = [[e["activation_stats"][p]["rms"] for e in evals] for p in points]
    fig = go.Figure(
        go.Heatmap(
            z=z, x=[e["step"] for e in evals], y=points,
            colorscale="Viridis", colorbar_title="RMS",
            hovertemplate="step %{x}<br>%{y}<br>RMS %{z:.3f}<extra></extra>",
        )
    )
    return base_layout(fig, "Residual-stream RMS across training (eval batches)", "optimizer step", "observation point", height=380)


def tokens_per_sec_figure(records: list[dict]) -> go.Figure:
    trains, _ = _split(records)
    fig = go.Figure(
        go.Scatter(x=[r["step"] for r in trains], y=[r["tokens_per_sec"] for r in trains],
                   mode="lines", line=dict(color=COLORS["sdpa"]))
    )
    return base_layout(fig, "Throughput (window-averaged; dips = eval/checkpoint steps)", "optimizer step", "tokens/sec")
