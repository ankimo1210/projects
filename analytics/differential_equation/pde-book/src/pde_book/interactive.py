"""Plotly-based interactive figures that survive static HTML export.

Unlike ``widgets`` (ipywidgets, live-kernel only), these return a Plotly
``go.Figure`` with a slider built from trace visibility, so they render in the
exported Jupyter Book too (the book loads require.js). In a notebook:

    import plotly.io as pio
    pio.renderers.default = "plotly_mimetype+notebook_connected"
    fig = interactive.plotly_fourier_square(); fig.show()
"""

from __future__ import annotations

import numpy as np

from . import datasets, grids, solvers


def _slider_figure(traces, labels, *, prefix, title, always_on=0, autorange_y=False, **layout):
    """Assemble traces into a visibility-slider Plotly figure (see ode_book version)."""
    import plotly.graph_objects as go

    n = len(traces) - always_on
    fig = go.Figure(traces)
    for i in range(len(traces)):
        fig.data[i].visible = (i == 0) or (i >= n)
    steps = []
    for i in range(n):
        vis = [(j == i) or (j >= n) for j in range(len(traces))]
        relayout = {"title.text": f"{title} {labels[i]}"}
        if autorange_y:
            relayout["yaxis.autorange"] = True
        steps.append(dict(method="update", args=[{"visible": vis}, relayout], label=str(labels[i])))
    fig.update_layout(
        sliders=[dict(active=0, currentvalue={"prefix": prefix}, pad={"t": 40}, steps=steps)],
        title=f"{title} {labels[0]}",
        template="plotly_white",
        height=460,
        **layout,
    )
    return fig


def plotly_fourier_square(n_values=None, L=np.pi):
    """Slider over the number of Fourier terms approximating a square wave."""
    import plotly.graph_objects as go

    if n_values is None:
        n_values = [1, 2, 3, 5, 8, 12, 20, 40]
    x = np.linspace(0, 2 * L, 800)
    target = np.where((x % (2 * L)) < L, 1.0, -1.0)
    traces = [
        go.Scatter(
            x=x,
            y=solvers.square_wave_partial_sum(x, n, L),
            line=dict(color="#d62728"),
            name=f"{n} terms",
        )
        for n in n_values
    ]
    traces.append(
        go.Scatter(
            x=x, y=target, mode="lines", line=dict(color="black", dash="dash"), name="square wave"
        )
    )
    return _slider_figure(
        traces,
        list(n_values),
        prefix="terms = ",
        always_on=1,
        title="Fourier partial sum, terms =",
        xaxis_title="x",
        yaxis_title="f(x)",
        yaxis_range=[-1.5, 1.5],
    )


def plotly_heat_stability(r_values=None, n=81, steps=80):
    """Slider over the diffusion number r of explicit heat (stable vs blow-up)."""
    import plotly.graph_objects as go

    if r_values is None:
        r_values = [0.2, 0.35, 0.45, 0.5, 0.55, 0.7]
    g = grids.Grid1D(0.0, 1.0, n)
    x, dx = g.x, g.dx
    u0 = datasets.bump(x, 0.5, 0.12)
    traces = []
    for r in r_values:
        U = solvers.solve_heat_explicit(u0, 1.0, dx, r * dx**2, steps)
        traces.append(go.Scatter(x=x, y=U[-1], line=dict(color="#d62728"), name=f"r={r}"))
    return _slider_figure(
        traces,
        list(r_values),
        prefix="r = ",
        autorange_y=True,
        title=f"explicit heat after {steps} steps (unstable if r>1/2), r =",
        xaxis_title="x",
        yaxis_title="u",
    )


def plotly_cfl_transport(c_values=None, n=201, c=1.0):
    """Slider over the CFL number C of upwind advection (stable vs blow-up)."""
    import plotly.graph_objects as go

    if c_values is None:
        c_values = [0.3, 0.6, 0.9, 1.0, 1.05, 1.2]
    g = grids.Grid1D(0.0, 1.0, n)
    x, dx = g.x, g.dx
    u0 = datasets.gaussian(x, 0.3, 0.05)
    traces = []
    for C in c_values:
        dt = C * dx / c
        steps = max(1, int(0.3 / dt))
        U = solvers.solve_transport(u0, c, dx, dt, steps, "upwind")
        traces.append(go.Scatter(x=x, y=U[-1], line=dict(color="#1f77b4"), name=f"C={C}"))
    traces.append(
        go.Scatter(x=x, y=u0, mode="lines", line=dict(color="black", dash="dash"), name="initial")
    )
    return _slider_figure(
        traces,
        list(c_values),
        prefix="CFL C = ",
        always_on=1,
        autorange_y=True,
        title="upwind advection (unstable if C>1), C =",
        xaxis_title="x",
        yaxis_title="u",
    )


def plotly_bs_surface(K=1.0, r=0.05, sigma=0.2, T=1.0):
    """Interactive 3-D Black-Scholes European call price surface V(S, t)."""
    import plotly.graph_objects as go
    from scipy.stats import norm

    S = np.linspace(0.2, 2.0, 100)
    t = np.linspace(0.0, 0.95, 80)
    SS, TT = np.meshgrid(S, t)
    tau = np.maximum(T - TT, 1e-12)
    d1 = (np.log(SS / K) + (r + 0.5 * sigma**2) * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)
    V = SS * norm.cdf(d1) - K * np.exp(-r * tau) * norm.cdf(d2)
    fig = go.Figure(data=[go.Surface(x=S, y=t, z=V, colorscale="Viridis")])
    fig.update_layout(
        title="Black-Scholes call price surface V(S, t) — drag to rotate",
        scene=dict(xaxis_title="S (price)", yaxis_title="t", zaxis_title="V"),
        template="plotly_white",
        height=560,
    )
    return fig


def plotly_field_evolution(
    x, U, step=2, duration=40, title="field evolution", ylim=None, dt=None, color="#d62728"
):
    """Play/slider animation of a 1-D field history U (shape (n_time, nx)).

    Renders in exported HTML (Plotly frames). ``step`` subsamples time for size.
    A fixed y-range keeps the motion readable. Returns a go.Figure.
    """
    import plotly.graph_objects as go

    x = np.asarray(x, dtype=float)
    U = np.asarray(U, dtype=float)
    idx = list(range(0, U.shape[0], step))
    if idx[-1] != U.shape[0] - 1:
        idx.append(U.shape[0] - 1)
    if ylim is None:
        pad = 0.08 * (U.max() - U.min() + 1e-9)
        ylim = (U.min() - pad, U.max() + pad)

    def label(k):
        return f"t={k * dt:.3f}" if dt is not None else f"step {k}"

    frames = [go.Frame(data=[go.Scatter(x=x, y=U[k])], name=str(k)) for k in idx]
    fig = go.Figure(
        data=[go.Scatter(x=x, y=U[idx[0]], mode="lines", line=dict(color=color, width=2))],
        frames=frames,
    )
    play = dict(
        label="Play",
        method="animate",
        args=[None, {"frame": {"duration": duration, "redraw": True}, "fromcurrent": True}],
    )
    pause = dict(
        label="Pause",
        method="animate",
        args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}],
    )
    slider = dict(
        active=0,
        pad={"t": 40},
        steps=[
            dict(
                method="animate",
                label=label(k),
                args=[[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            )
            for k in idx
        ],
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=460,
        xaxis_title="x",
        yaxis_title="u",
        yaxis_range=list(ylim),
        updatemenus=[dict(type="buttons", direction="left", x=0.0, y=1.15, buttons=[play, pause])],
        sliders=[slider],
    )
    return fig


def _anim_controls(idx_labels, duration=500):
    """Play/Pause buttons + a slider for a frame animation. idx_labels: list of (name, label)."""
    play = dict(
        label="Play",
        method="animate",
        args=[None, {"frame": {"duration": duration, "redraw": True}, "fromcurrent": True}],
    )
    pause = dict(
        label="Pause",
        method="animate",
        args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}],
    )
    slider = dict(
        active=0,
        pad={"t": 40},
        steps=[
            dict(
                method="animate",
                label=lab,
                args=[[name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            )
            for name, lab in idx_labels
        ],
    )
    return (
        [dict(type="buttons", direction="left", x=0.0, y=1.18, buttons=[play, pause])],
        [slider],
    )


def plotly_riemann_convergence(f, a, b, n_values=None):
    """Animate midpoint Riemann rectangles converging to the integral as n grows."""
    import plotly.graph_objects as go

    if n_values is None:
        n_values = [2, 4, 8, 16, 32, 64]
    xs = np.linspace(a, b, 400)
    curve = go.Scatter(x=xs, y=f(xs), mode="lines", line=dict(color="black", width=2), name="f(x)")

    def bars(n):
        edges = np.linspace(a, b, n + 1)
        mid = 0.5 * (edges[:-1] + edges[1:])
        return go.Bar(
            x=mid,
            y=f(mid),
            width=(b - a) / n,
            marker_color="#1f77b4",
            opacity=0.45,
            name="midpoint sum",
        ), float(np.sum(f(mid)) * (b - a) / n)

    frames = []
    for n in n_values:
        bar, val = bars(n)
        frames.append(
            go.Frame(
                data=[bar],
                name=str(n),
                traces=[1],
                layout=dict(title=dict(text=f"midpoint Riemann sum: n={n}, sum={val:.4f}")),
            )
        )
    fig = go.Figure(data=[curve, bars(n_values[0])[0]], frames=frames)
    menus, sliders = _anim_controls([(str(n), f"n={n}") for n in n_values])
    fig.update_layout(
        title="midpoint Riemann sum converging to the integral",
        template="plotly_white",
        height=460,
        xaxis_title="x",
        yaxis_title="f(x)",
        updatemenus=menus,
        sliders=sliders,
        bargap=0,
    )
    return fig


def plotly_secant_to_tangent(f, x0, h_values=None):
    """Animate secant lines through x0 shrinking onto the tangent as h -> 0."""
    import plotly.graph_objects as go

    if h_values is None:
        h_values = [2.0, 1.0, 0.5, 0.25, 0.1, 0.02]
    span = max(abs(h) for h in h_values) * 1.4
    xs = np.linspace(x0 - span, x0 + span, 200)
    f0 = float(f(x0))
    hmin = min(h_values)
    tan = (f(x0 + hmin) - f(x0 - hmin)) / (2 * hmin)
    curve = go.Scatter(x=xs, y=f(xs), mode="lines", line=dict(color="black", width=2), name="f(x)")
    tangent = go.Scatter(
        x=xs,
        y=f0 + tan * (xs - x0),
        mode="lines",
        line=dict(color="#2ca02c", dash="dash"),
        name="tangent",
    )
    pt = go.Scatter(
        x=[x0], y=[f0], mode="markers", marker=dict(color="black", size=8), showlegend=False
    )

    def secant(h):
        s = (f(x0 + h) - f0) / h
        return go.Scatter(
            x=xs,
            y=f0 + s * (xs - x0),
            mode="lines",
            line=dict(color="#d62728", width=2),
            name="secant",
        )

    frames = [go.Frame(data=[secant(h)], name=f"{h:g}", traces=[3]) for h in h_values]
    fig = go.Figure(data=[curve, tangent, pt, secant(h_values[0])], frames=frames)
    menus, sliders = _anim_controls([(f"{h:g}", f"h={h:g}") for h in h_values])
    fig.update_layout(
        title="secant slope -> tangent slope as h -> 0",
        template="plotly_white",
        height=460,
        xaxis_title="x",
        yaxis_title="f(x)",
        updatemenus=menus,
        sliders=sliders,
    )
    return fig
