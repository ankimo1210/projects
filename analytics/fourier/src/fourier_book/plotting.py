"""Shared plotting helpers (matplotlib).

Figure text is kept in English so no Japanese-font setup is required; the
notebook prose around each figure carries the Japanese explanation. Helpers
return the Axes/Figure so notebooks can tweak them further.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

WAVE_COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b"]


def plot_signal(
    t, x, ax=None, title=None, xlabel="time t [s]", ylabel="amplitude", color=WAVE_COLORS[0], **kw
):
    """Plot one signal against time."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 2.8))
    ax.plot(t, x, color=color, **kw)
    ax.axhline(0, color="gray", lw=0.6)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(alpha=0.25)
    return ax


def plot_components(t, components, labels=None, ax=None, title="wave components"):
    """Overlay several wave components (the pieces being summed)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3))
    for i, comp in enumerate(components):
        lbl = labels[i] if labels is not None else f"component {i + 1}"
        ax.plot(t, comp, color=WAVE_COLORS[i % len(WAVE_COLORS)], lw=1.5, label=lbl)
    ax.axhline(0, color="gray", lw=0.6)
    ax.set_xlabel("time t [s]")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.25)
    return ax


def plot_sum_of_waves(t, components, labels=None, figsize=(9, 5)):
    """Top: each component overlaid; bottom: their sum. The core 'addition' picture."""
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
    plot_components(t, components, labels=labels, ax=axes[0], title="components")
    total = np.sum(components, axis=0)
    axes[1].plot(t, total, color="black", lw=1.8)
    axes[1].axhline(0, color="gray", lw=0.6)
    axes[1].set_title("their sum")
    axes[1].set_xlabel("time t [s]")
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    return fig, axes


def plot_spectrum(
    freqs,
    amp,
    ax=None,
    title="amplitude spectrum",
    xlabel="frequency f [Hz]",
    ylabel="amplitude",
    stem=True,
    xlim=None,
):
    """Plot a one-sided spectrum (stem by default — discrete frequency content)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 2.8))
    if stem:
        ax.stem(freqs, amp, basefmt=" ", markerfmt="o", linefmt="-")
    else:
        ax.plot(freqs, amp, color=WAVE_COLORS[1])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if xlim is not None:
        ax.set_xlim(*xlim)
    ax.grid(alpha=0.25)
    return ax


def plot_time_and_freq(t, x, freqs, amp, xlim_freq=None, stem=True):
    """Side-by-side time domain (left) and frequency domain (right)."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.2))
    plot_signal(t, x, ax=axes[0], title="time domain")
    plot_spectrum(freqs, amp, ax=axes[1], title="frequency domain", stem=stem, xlim=xlim_freq)
    fig.tight_layout()
    return fig, axes


def plot_partial_sums(t, partials, orders, target=None, figsize=(9, 4)):
    """Successive Fourier partial sums converging to a target (shows Gibbs)."""
    fig, ax = plt.subplots(figsize=figsize)
    if target is not None:
        ax.plot(t, target, color="black", lw=2.0, label="target", alpha=0.6)
    for i, (p, k) in enumerate(zip(partials, orders, strict=True)):
        ax.plot(t, p, color=WAVE_COLORS[i % len(WAVE_COLORS)], lw=1.2, label=f"N = {k}")
    ax.set_xlabel("time t [s]")
    ax.set_title("Fourier partial sums")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.25)
    return fig, ax


def plot_coefficient_decay(ns, magnitudes, ax=None, title="coefficient decay |c_n|"):
    """Log-scale stem of coefficient magnitudes vs index — smoothness as decay rate."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 3))
    ax.semilogy(ns, magnitudes + 1e-18, "o-", color=WAVE_COLORS[3], ms=4)
    ax.set_xlabel("harmonic index n")
    ax.set_ylabel("|c_n| (log)")
    ax.set_title(title)
    ax.grid(alpha=0.25, which="both")
    return ax


def plot_spectrogram(f, t, s_db, ax=None, title="spectrogram", fmax=None, cmap="magma"):
    """Plot an STFT magnitude (dB) as a time-frequency heat map."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3.5))
    mesh = ax.pcolormesh(t, f, s_db, shading="auto", cmap=cmap)
    ax.set_xlabel("time t [s]")
    ax.set_ylabel("frequency f [Hz]")
    ax.set_title(title)
    if fmax is not None:
        ax.set_ylim(0, fmax)
    plt.colorbar(mesh, ax=ax, label="magnitude [dB]")
    return ax


def plot_image_and_spectrum(img, figsize=(9, 4), cmap="gray"):
    """Image alongside its centered log-magnitude 2-D FFT."""
    spec = np.fft.fftshift(np.fft.fft2(img))
    log_mag = np.log1p(np.abs(spec))
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    axes[0].imshow(img, cmap=cmap)
    axes[0].set_title("image (space domain)")
    axes[0].axis("off")
    im = axes[1].imshow(log_mag, cmap="magma")
    axes[1].set_title("2-D FFT log-magnitude (centered)")
    axes[1].axis("off")
    plt.colorbar(im, ax=axes[1], fraction=0.046)
    fig.tight_layout()
    return fig, axes
