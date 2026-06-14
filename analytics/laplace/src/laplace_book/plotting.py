"""Shared plotting helpers (matplotlib, plus one Plotly s-surface).

Figure labels are kept in English so no Japanese font setup is required; the
surrounding notebook text carries the Japanese explanation. The figures are
deliberately about *concepts* -- decay rate, the meaning of sigma and omega on
the s-plane, pole location vs. response shape, convolution -- not decoration.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

STABLE_COLOR = "#2ca02c"
UNSTABLE_COLOR = "#d62728"
ACCENT = "#1f77b4"


# --------------------------------------------------------------------------- #
# Exponentials and complex frequency (chapter 01).
# --------------------------------------------------------------------------- #
def plot_exponentials(t, sigmas, ax=None):
    """Plot e^{sigma t} for several sigma: growth (sigma>0) vs decay (sigma<0)."""
    t = np.asarray(t, dtype=float)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for sigma in sigmas:
        ax.plot(t, np.exp(sigma * t), label=f"sigma = {sigma:+.1f}")
    ax.axhline(1.0, color="gray", lw=0.8, ls=":")
    ax.set_xlabel("t")
    ax.set_ylabel("e^{sigma t}")
    ax.set_title("Exponential growth / decay")
    ax.legend()
    ax.grid(alpha=0.25)
    return ax


def plot_damped_oscillation(t, sigma, omega, ax=None):
    """e^{sigma t} cos(omega t) with its envelope +/- e^{sigma t}."""
    t = np.asarray(t, dtype=float)
    env = np.exp(sigma * t)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    ax.plot(t, env * np.cos(omega * t), color=ACCENT, label="e^{sigma t} cos(omega t)")
    ax.plot(t, env, color="gray", ls="--", lw=1, label="envelope +/- e^{sigma t}")
    ax.plot(t, -env, color="gray", ls="--", lw=1)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("t")
    ax.set_ylabel("amplitude")
    ax.set_title(f"sigma = {sigma:+.2f}, omega = {omega:.2f}")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.25)
    return ax


# --------------------------------------------------------------------------- #
# The s-plane (chapters 01, 06).
# --------------------------------------------------------------------------- #
def plot_s_plane(poles=(), zeros=(), ax=None, lim=None, annotate_regions=True, title="s-plane"):
    """Pole-zero map. Poles = 'x', zeros = 'o'. Shades stable (LHP) vs unstable (RHP)."""
    poles = (
        np.atleast_1d(np.asarray(poles, dtype=complex))
        if len(poles)
        else np.array([], dtype=complex)
    )
    zeros = (
        np.atleast_1d(np.asarray(zeros, dtype=complex))
        if len(zeros)
        else np.array([], dtype=complex)
    )
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    pts = np.concatenate([poles, zeros, [1 + 1j]])
    if lim is None:
        lim = 1.4 * max(1.0, np.max(np.abs(pts)))
    if annotate_regions:
        ax.axvspan(-lim, 0, color=STABLE_COLOR, alpha=0.07)
        ax.axvspan(0, lim, color=UNSTABLE_COLOR, alpha=0.07)
        ax.text(-lim * 0.95, lim * 0.88, "LHP: decay (stable)", color=STABLE_COLOR, fontsize=9)
        ax.text(lim * 0.05, lim * 0.88, "RHP: growth (unstable)", color=UNSTABLE_COLOR, fontsize=9)
    ax.axvline(0, color="k", lw=1.2)
    ax.axhline(0, color="gray", lw=0.8)
    if poles.size:
        ax.scatter(poles.real, poles.imag, marker="x", s=90, color="k", label="poles", zorder=3)
    if zeros.size:
        ax.scatter(
            zeros.real,
            zeros.imag,
            marker="o",
            s=80,
            facecolors="none",
            edgecolors=ACCENT,
            label="zeros",
            zorder=3,
        )
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("Re(s) = sigma")
    ax.set_ylabel("Im(s) = omega")
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    if poles.size or zeros.size:
        ax.legend(loc="lower right", fontsize=8)
    return ax


def plot_pole_and_response(sigma, omega, t, axes=None):
    """Two panels: a conjugate pole pair on the s-plane, and the response it gives.

    The response is e^{sigma t} cos(omega t): real part sigma sets decay/growth,
    imaginary part omega sets oscillation -- exactly the pole's coordinates.
    """
    t = np.asarray(t, dtype=float)
    if axes is None:
        _, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax_s, ax_t = axes
    pole_pair = [complex(sigma, omega), complex(sigma, -omega)] if omega else [complex(sigma, 0)]
    plot_s_plane(poles=pole_pair, ax=ax_s, title="pole location")
    plot_damped_oscillation(t, sigma, omega, ax=ax_t)
    return axes


# --------------------------------------------------------------------------- #
# Responses and convolution (chapters 04, 05).
# --------------------------------------------------------------------------- #
def plot_time_responses(t, ys, labels=None, ax=None, title=None, ylabel="y(t)"):
    """Overlay several time responses y(t) on one axis."""
    t = np.asarray(t, dtype=float)
    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 4))
    for i, y in enumerate(ys):
        lab = None if labels is None else labels[i]
        ax.plot(t, np.asarray(y, dtype=float), label=lab)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("t")
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if labels is not None:
        ax.legend()
    ax.grid(alpha=0.25)
    return ax


def plot_convolution(t, f, g, conv, axes=None):
    """Show inputs f, g and their convolution (f * g) on stacked panels."""
    t = np.asarray(t, dtype=float)
    if axes is None:
        _, axes = plt.subplots(3, 1, figsize=(7, 6), sharex=True)
    axes[0].plot(t, f, color=ACCENT)
    axes[0].set_ylabel("f(t)")
    axes[1].plot(t, g, color="#ff7f0e")
    axes[1].set_ylabel("g(t)")
    axes[2].plot(t, conv, color=STABLE_COLOR)
    axes[2].set_ylabel("(f * g)(t)")
    axes[2].set_xlabel("t")
    for ax in axes:
        ax.grid(alpha=0.25)
    axes[0].set_title("Convolution in time = multiplication in s")
    return axes


def plot_bode(sys, w=None, axes=None):
    """Bode magnitude/phase from a transfer function (entry-level frequency view)."""
    from scipy import signal

    w, mag, phase = signal.bode(sys, w=w)
    if axes is None:
        _, axes = plt.subplots(2, 1, figsize=(6.5, 5), sharex=True)
    axes[0].semilogx(w, mag, color=ACCENT)
    axes[0].set_ylabel("magnitude [dB]")
    axes[0].grid(alpha=0.25, which="both")
    axes[1].semilogx(w, phase, color="#ff7f0e")
    axes[1].set_ylabel("phase [deg]")
    axes[1].set_xlabel("omega [rad/s]")
    axes[1].grid(alpha=0.25, which="both")
    axes[0].set_title("Bode plot")
    return axes


def plot_root_locus(g, k_values, ax=None):
    """Plot how the closed-loop poles of unity feedback around k*G move with k.

    'x' marks the open-loop poles (k=0 start), 'o' the open-loop zeros (where
    branches end). The colored trail is the locus; crossing the imaginary axis
    marks the gain at which the loop goes unstable.
    """
    from . import systems

    k_values, locus = systems.root_locus(g, k_values)
    p0, z0 = systems.poles(g), systems.zeros(g)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    pts = np.concatenate(locus)
    sc = ax.scatter(
        pts.real,
        pts.imag,
        c=np.repeat(k_values, [len(r) for r in locus]),
        cmap="viridis",
        s=10,
        alpha=0.7,
    )
    ax.scatter(
        p0.real, p0.imag, marker="x", s=90, color="k", zorder=3, label="open-loop poles (k=0)"
    )
    if z0.size:
        ax.scatter(
            z0.real,
            z0.imag,
            marker="o",
            s=80,
            facecolors="none",
            edgecolors=UNSTABLE_COLOR,
            zorder=3,
            label="open-loop zeros",
        )
    ax.axvline(0, color="k", lw=1.2)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("Re(s)")
    ax.set_ylabel("Im(s)")
    ax.set_title("Root locus (closed-loop poles vs gain k)")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=8)
    plt.colorbar(sc, ax=ax, label="gain k", fraction=0.046, pad=0.04)
    return ax


def plot_nyquist(sys, w=None, ax=None):
    """Nyquist plot: the locus of the open-loop L(jw) in the complex plane.

    Encirclements of the -1 point predict closed-loop instability. The dashed
    branch is the mirror image for w < 0.
    """
    from . import systems

    if w is None:
        w = np.logspace(-2, 3, 2000)
    w = np.asarray(w, dtype=float)
    H = systems.evaluate(sys, 1j * w)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    ax.plot(H.real, H.imag, color=ACCENT, label="L(jw), w > 0")
    ax.plot(H.real, -H.imag, color=ACCENT, ls="--", alpha=0.6, label="w < 0")
    ax.scatter([-1.0], [0.0], color=UNSTABLE_COLOR, marker="+", s=140, zorder=3, label="-1 point")
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_xlabel("Re L(jw)")
    ax.set_ylabel("Im L(jw)")
    ax.set_title("Nyquist plot")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    return ax


# --------------------------------------------------------------------------- #
# One Plotly figure: |F(s)| as a surface over the s-plane.
# --------------------------------------------------------------------------- #
def surface_abs_F(F_callable, sigma_range=(-2, 2), omega_range=(-6, 6), n=80):
    """Interactive |F(s)| surface over a patch of the s-plane (poles spike up).

    ``F_callable`` maps a complex array s -> complex F(s). Returns a Plotly
    Figure; magnitude is clipped so poles do not blow the colour scale.
    """
    import plotly.graph_objects as go

    sig = np.linspace(*sigma_range, n)
    om = np.linspace(*omega_range, n)
    S = sig[None, :] + 1j * om[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        Z = np.abs(F_callable(S))
    Z = np.clip(Z, 0, np.nanpercentile(Z[np.isfinite(Z)], 97))
    fig = go.Figure(data=[go.Surface(x=sig, y=om, z=Z, colorscale="Viridis", showscale=False)])
    fig.update_layout(
        title="|F(s)| over the s-plane (peaks = poles)",
        scene={
            "xaxis_title": "sigma = Re(s)",
            "yaxis_title": "omega = Im(s)",
            "zaxis_title": "|F(s)|",
        },
        height=520,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )
    return fig


# --------------------------------------------------------------------------- #
# Animations (matplotlib FuncAnimation; display with HTML(anim.to_jshtml())).
# --------------------------------------------------------------------------- #
def animate_pole_crossing(omega=3.0, sigmas=None, t_max=12.0, n=300):
    """Animate a conjugate pole pair sweeping across the imaginary axis.

    As sigma goes from negative (decay) through 0 (sustained) to positive
    (growth), the pole position and the response e^{sigma t} cos(omega t) change
    together -- the stability boundary made visual. Returns a FuncAnimation.
    """
    from matplotlib.animation import FuncAnimation

    if sigmas is None:
        sigmas = np.linspace(-0.6, 0.4, 18)
    t = np.linspace(0.0, t_max, n)
    lim = 1.5 * max(1.0, omega)
    ymax = float(np.exp(max(sigmas) * t_max))
    fig, (ax_s, ax_t) = plt.subplots(1, 2, figsize=(11, 4.2))

    def draw(i):
        ax_s.clear()
        ax_t.clear()
        sig = sigmas[i]
        plot_s_plane(
            poles=[complex(sig, omega), complex(sig, -omega)],
            ax=ax_s,
            lim=lim,
            title=f"pole: sigma = {sig:+.2f}",
        )
        env = np.exp(sig * t)
        ax_t.plot(t, env * np.cos(omega * t), color=ACCENT)
        ax_t.plot(t, env, "--", color="gray", lw=1)
        ax_t.plot(t, -env, "--", color="gray", lw=1)
        ax_t.axhline(0, color="gray", lw=0.8)
        ax_t.set_ylim(-ymax, ymax)
        ax_t.set_xlabel("t")
        ax_t.set_ylabel("response")
        regime = "stable" if sig < -1e-9 else ("marginal" if abs(sig) <= 1e-9 else "unstable")
        ax_t.set_title(f"response ({regime})")
        ax_t.grid(alpha=0.25)
        fig.tight_layout()

    return FuncAnimation(fig, draw, frames=len(sigmas), interval=120)


def animate_resonance(omega_n=3.0, zeta=0.05, drive_freqs=None, t_max=24.0, n=700):
    """Animate driving a lightly-damped 2nd-order system at sweeping frequencies.

    The response amplitude peaks as the drive frequency approaches omega_n
    (resonance), tracked by |H(i*omega_drive)|. Returns a FuncAnimation.
    """
    from matplotlib.animation import FuncAnimation

    from . import systems

    if drive_freqs is None:
        drive_freqs = np.linspace(0.3 * omega_n, 1.8 * omega_n, 18)
    t = np.linspace(0.0, t_max, n)
    sys = systems.second_order(omega_n, zeta)
    gains = np.array([abs(systems.evaluate(sys, 1j * wd)) for wd in drive_freqs])
    ymax = 1.2 * float(gains.max())
    fig, ax = plt.subplots(figsize=(7.5, 4.2))

    def draw(i):
        ax.clear()
        wd = drive_freqs[i]
        u = np.sin(wd * t)
        y = systems.forced_response(sys, u, t)
        ax.plot(t, y, color=ACCENT, label="response")
        ax.plot(t, u, color="gray", lw=0.8, alpha=0.6, label="drive")
        ax.set_ylim(-ymax, ymax)
        ax.set_title(f"drive w = {wd:.2f}  (w_n = {omega_n}):  |H(iw)| = {gains[i]:.2f}")
        ax.set_xlabel("t")
        ax.set_ylabel("amplitude")
        ax.legend(loc="upper right")
        ax.grid(alpha=0.25)
        fig.tight_layout()

    return FuncAnimation(fig, draw, frames=len(drive_freqs), interval=150)


# --------------------------------------------------------------------------- #
# Plotly figures for the analytics report portal (self-contained, slider-based).
# --------------------------------------------------------------------------- #
def _plotly_slider(labels, frames_data, title, xaxis, yaxis, active=0, prefix=""):
    """Assemble a Plotly slider figure from per-frame trace lists."""
    import plotly.graph_objects as go

    frames = [go.Frame(name=labels[i], data=frames_data[i]) for i in range(len(labels))]
    fig = go.Figure(data=frames_data[active], frames=frames)
    steps = [
        {
            "args": [[labels[i]], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": labels[i],
            "method": "animate",
        }
        for i in range(len(labels))
    ]
    fig.update_layout(
        title=title,
        xaxis_title=xaxis,
        yaxis_title=yaxis,
        height=440,
        sliders=[{"active": active, "currentvalue": {"prefix": prefix}, "steps": steps}],
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_pole_response_slider(omega=3.0, t_max=12.0, n=300):
    """Slider over sigma: the response e^{sigma t} cos(omega t) morphs decay -> growth."""
    import plotly.graph_objects as go

    sigmas = np.round(np.linspace(-0.6, 0.4, 11), 2)
    t = np.linspace(0.0, t_max, n)
    frames_data = []
    for sig in sigmas:
        env = np.exp(sig * t)
        frames_data.append(
            [
                go.Scatter(x=t, y=env * np.cos(omega * t), name="response", line={"color": ACCENT}),
                go.Scatter(x=t, y=env, name="envelope", line={"color": "gray", "dash": "dash"}),
                go.Scatter(x=t, y=-env, showlegend=False, line={"color": "gray", "dash": "dash"}),
            ]
        )
    return _plotly_slider(
        [f"{s:+.2f}" for s in sigmas],
        frames_data,
        "sigma sweeps the pole across the imaginary axis (decay -> growth)",
        "t",
        "response",
        active=len(sigmas) // 2,
        prefix="sigma = ",
    )


def plotly_step_response_slider(wn=1.5, t_max=14.0, n=400):
    """Slider over the damping ratio zeta of a second-order step response."""
    import plotly.graph_objects as go

    from . import systems

    zetas = np.round(np.linspace(0.1, 2.0, 11), 2)
    t = np.linspace(0.0, t_max, n)
    frames_data = []
    for z in zetas:
        y = systems.step_response(systems.second_order(wn, z), t)
        frames_data.append(
            [
                go.Scatter(x=t, y=y, name="step response", line={"color": ACCENT}),
                go.Scatter(
                    x=t, y=np.ones_like(t), name="target", line={"color": "gray", "dash": "dot"}
                ),
            ]
        )
    return _plotly_slider(
        [f"{z:.2f}" for z in zetas],
        frames_data,
        "Second-order step response vs damping ratio zeta",
        "t",
        "y(t)",
        active=2,
        prefix="zeta = ",
    )


def plotly_pole_zero(num=(1.0, 1.0), den=(1.0, 1.0, 4.0)):
    """Pole-zero map of a sample H(s) in the s-plane (poles = x, zeros = o)."""
    import plotly.graph_objects as go

    from . import systems

    H = systems.tf(list(num), list(den))
    p, z = systems.poles(H), systems.zeros(H)
    fig = go.Figure()
    fig.add_vline(x=0, line={"color": "black", "width": 1})
    fig.add_trace(
        go.Scatter(
            x=p.real,
            y=p.imag,
            mode="markers",
            name="poles",
            marker={"symbol": "x", "size": 12, "color": "black"},
        )
    )
    if z.size:
        fig.add_trace(
            go.Scatter(
                x=z.real,
                y=z.imag,
                mode="markers",
                name="zeros",
                marker={"symbol": "circle-open", "size": 12, "color": ACCENT},
            )
        )
    fig.update_layout(
        title="Pole-zero map (left half-plane = stable)",
        xaxis_title="Re(s)",
        yaxis_title="Im(s)",
        height=440,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def plotly_abs_F_surface():
    """The |F(s)| surface for F = 1/((s+1)^2+9): poles spike over the s-plane."""
    return surface_abs_F(
        lambda S: 1.0 / ((S + 1.0) ** 2 + 9.0), sigma_range=(-3, 1), omega_range=(-7, 7), n=70
    )


def plotly_root_locus(num=(1.0,), den=(1.0, 1.0, 0.0), k_max=12.0):
    """Root locus of unity feedback around k*G, colored by gain k."""
    import plotly.graph_objects as go

    from . import systems

    G = systems.tf(list(num), list(den))
    ks = np.linspace(0.0, k_max, 60)
    _, locus = systems.root_locus(G, ks)
    pts = np.concatenate(locus)
    kcol = np.repeat(ks, [len(r) for r in locus])
    p0, z0 = systems.poles(G), systems.zeros(G)
    fig = go.Figure()
    fig.add_vline(x=0, line={"color": "black", "width": 1})
    fig.add_trace(
        go.Scatter(
            x=pts.real,
            y=pts.imag,
            mode="markers",
            name="closed-loop poles",
            marker={
                "size": 5,
                "color": kcol,
                "colorscale": "Viridis",
                "colorbar": {"title": "k"},
                "showscale": True,
            },
        )
    )
    fig.add_trace(
        go.Scatter(
            x=p0.real,
            y=p0.imag,
            mode="markers",
            name="open-loop poles (k=0)",
            marker={"symbol": "x", "size": 12, "color": "black"},
        )
    )
    if z0.size:
        fig.add_trace(
            go.Scatter(
                x=z0.real,
                y=z0.imag,
                mode="markers",
                name="open-loop zeros",
                marker={"symbol": "circle-open", "size": 12, "color": UNSTABLE_COLOR},
            )
        )
    fig.update_layout(
        title="Root locus: closed-loop poles vs gain k",
        xaxis_title="Re(s)",
        yaxis_title="Im(s)",
        height=440,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def plotly_rlc_step_slider(L=1e-3, C=1e-6, t_max=4e-3, n=500):
    """Slider over R: series-RLC step response cycles through the damping regimes."""
    import plotly.graph_objects as go

    from . import circuits, systems

    resistors = [10.0, 30.0, 63.2, 150.0, 400.0]
    t = np.linspace(0.0, t_max, n)
    frames_data, labels = [], []
    for R in resistors:
        y = systems.step_response(circuits.rlc_series_vc(R, L, C), t)
        regime = circuits.rlc_params(R, L, C)["regime"]
        frames_data.append(
            [
                go.Scatter(x=t * 1e3, y=y, name="v_C / V_in", line={"color": ACCENT}),
                go.Scatter(
                    x=t * 1e3,
                    y=np.ones_like(t),
                    showlegend=False,
                    line={"color": "gray", "dash": "dot"},
                ),
            ]
        )
        labels.append(f"R={R:g} ({regime})")
    return _plotly_slider(
        labels,
        frames_data,
        "Series RLC step response: damping regime vs R",
        "t [ms]",
        "v_C / V_in",
        active=0,
        prefix="",
    )
