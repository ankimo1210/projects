"""Plotly-based interactive figures that survive static HTML export.

Unlike ``widgets`` (ipywidgets, live-kernel only), these return a Plotly
``go.Figure`` with a slider built from trace visibility, so they render in the
exported Jupyter Book too (the book loads require.js). In a notebook:

    import plotly.io as pio
    pio.renderers.default = "plotly_mimetype+notebook_connected"
    fig = interactive.plotly_logistic_r(); fig.show()
"""

from __future__ import annotations

import numpy as np

from . import solvers, systems


def _slider_figure(traces, labels, *, prefix, title, always_on=0, **layout):
    """Assemble traces into a visibility-slider Plotly figure.

    ``traces`` is a list of go.Scatter; the last ``always_on`` traces stay
    visible for every slider step (e.g. a reference line).
    """
    import plotly.graph_objects as go

    n = len(traces) - always_on
    fig = go.Figure(traces)
    for i in range(len(traces)):
        fig.data[i].visible = (i == 0) or (i >= n)
    steps = []
    for i in range(n):
        vis = [(j == i) or (j >= n) for j in range(len(traces))]
        steps.append(
            dict(
                method="update",
                args=[{"visible": vis}, {"title.text": f"{title} {labels[i]}"}],
                label=str(labels[i]),
            )
        )
    fig.update_layout(
        sliders=[dict(active=0, currentvalue={"prefix": prefix}, pad={"t": 40}, steps=steps)],
        title=f"{title} {labels[0]}",
        template="plotly_white",
        height=460,
        **layout,
    )
    return fig


def plotly_logistic_r(r_values=None, K=1.0, y0=0.1, t_end=12.0):
    """Slider over the growth rate r of the logistic equation (static-HTML safe)."""
    import plotly.graph_objects as go

    if r_values is None:
        r_values = np.round(np.linspace(0.2, 2.0, 10), 2)
    t = np.linspace(0, t_end, 200)
    traces = [
        go.Scatter(
            x=t,
            y=solvers.rk4(systems.logistic(r, K), [y0], t)[:, 0],
            line=dict(color="#d62728", width=3),
            name=f"r={r}",
        )
        for r in r_values
    ]
    traces.append(
        go.Scatter(
            x=[0, t_end], y=[K, K], mode="lines", line=dict(color="#2ca02c", dash="dash"), name="K"
        )
    )
    fig = _slider_figure(
        traces,
        list(r_values),
        prefix="r = ",
        always_on=1,
        title="logistic dy/dt = r y(1 - y/K), r =",
        xaxis_title="t",
        yaxis_title="y",
        yaxis_range=[0, 1.6 * K],
    )
    return fig


def plotly_method_dt(n_values=None):
    """Slider over the number of Euler steps for dy/dt=-1.5 y vs the exact decay."""
    import plotly.graph_objects as go

    if n_values is None:
        n_values = [4, 6, 8, 12, 20, 40, 80]
    rate, y0 = 1.5, 1.0
    f = systems.exponential(-rate)
    traces = []
    for n in n_values:
        t = np.linspace(0, 5, int(n))
        traces.append(
            go.Scatter(
                x=t,
                y=solvers.euler(f, [y0], t)[:, 0],
                mode="lines+markers",
                line=dict(color="#1f77b4"),
                name=f"Euler n={n}",
            )
        )
    t_fine = np.linspace(0, 5, 400)
    traces.append(
        go.Scatter(
            x=t_fine,
            y=y0 * np.exp(-rate * t_fine),
            mode="lines",
            line=dict(color="black", width=2),
            name="exact",
        )
    )
    return _slider_figure(
        traces,
        list(n_values),
        prefix="steps = ",
        always_on=1,
        title="Euler vs exact decay, steps =",
        xaxis_title="t",
        yaxis_title="y",
    )


def plotly_lorenz_3d(t_end=40.0, n=8000, y0=(1.0, 1.0, 1.0)):
    """Interactive 3-D Lorenz attractor (drag to rotate; renders in exported HTML)."""
    import plotly.graph_objects as go

    t = np.linspace(0, t_end, n)
    Y = solvers.solve(systems.lorenz(), list(y0), t, rtol=1e-9, atol=1e-9)
    fig = go.Figure(
        go.Scatter3d(
            x=Y[:, 0],
            y=Y[:, 1],
            z=Y[:, 2],
            mode="lines",
            line=dict(color=t, colorscale="Viridis", width=2),
        )
    )
    fig.update_layout(
        title="Lorenz attractor (sigma=10, rho=28, beta=8/3) — drag to rotate",
        scene=dict(xaxis_title="x", yaxis_title="y", zaxis_title="z"),
        template="plotly_white",
        height=560,
    )
    return fig
