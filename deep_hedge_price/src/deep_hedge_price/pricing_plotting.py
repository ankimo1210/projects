"""Compact Plotly figures for the standalone pricing report."""

from __future__ import annotations

import plotly.graph_objects as go


def error_comparison_figure(evaluation):
    """Polynomial vs neural price MAE on the common test split."""
    split = evaluation["splits"]["test"]
    figure = go.Figure(
        [
            go.Bar(
                x=["Polynomial", "Neural"],
                y=[split["polynomial_price"]["mae"], split["neural_price"]["mae"]],
                marker_color=["#64748B", "#2563EB"],
            )
        ]
    )
    figure.update_layout(
        template="plotly_white",
        title="Price error — common test split",
        yaxis_title="MAE (K units)",
    )
    return figure


def greek_error_figure(evaluation):
    """Autodiff Greek MAE bars on the test split."""
    metrics = evaluation["splits"]["test"]["greeks"]
    figure = go.Figure(
        go.Bar(
            x=list(metrics), y=[metrics[name]["mae"] for name in metrics], marker_color="#7C3AED"
        )
    )
    figure.update_layout(template="plotly_white", title="Autodiff Greek errors", yaxis_title="MAE")
    return figure


def hard_check_figure(evaluation):
    """Violation rate per canonical hard arbitrage check."""
    checks = evaluation["hard_validation"]["checks"]
    figure = go.Figure(
        go.Bar(
            x=[check["name"] for check in checks],
            y=[check["violation_rate"] for check in checks],
            marker_color=["#DC2626" if check["n_violations"] else "#16A34A" for check in checks],
        )
    )
    figure.update_layout(
        template="plotly_white", title="Canonical hard checks", yaxis_title="Violation rate"
    )
    return figure


def speed_figure(evaluation):
    """Batch-latency comparison across pricing methods."""
    figure = go.Figure()
    methods = (
        ("analytic", "#111827"),
        ("heston_cos", "#D97706"),
        ("monte_carlo", "#DC2626"),
        ("polynomial", "#64748B"),
        ("neural", "#2563EB"),
    )
    for name, color in methods:
        if name not in evaluation["benchmark"]:
            continue
        rows = evaluation["benchmark"][name]
        figure.add_trace(
            go.Scatter(
                x=[row["batch_size"] for row in rows],
                y=[row["median_ms"] for row in rows],
                mode="lines+markers",
                name=name,
                line={"color": color},
            )
        )
    figure.update_layout(
        template="plotly_white",
        title="Common-harness pricing benchmark",
        xaxis_title="Batch size",
        yaxis_title="Median ms",
    )
    return figure
