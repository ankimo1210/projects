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
    poles = np.atleast_1d(np.asarray(poles, dtype=complex)) if len(poles) else np.array([], dtype=complex)
    zeros = np.atleast_1d(np.asarray(zeros, dtype=complex)) if len(zeros) else np.array([], dtype=complex)
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
            zeros.real, zeros.imag, marker="o", s=80, facecolors="none", edgecolors=ACCENT,
            label="zeros", zorder=3,
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
