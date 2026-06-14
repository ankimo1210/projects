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


def plot_spacetime(field, x, t, title="u(x, t)", xlabel="x", cmap="RdBu_r"):
    """Space-time heatmap of a 1-D field's evolution (space across, time upward).

    ``field`` has shape ``(len(t), len(x))``. Makes diffusion / wave propagation
    visible at a glance: horizontal smearing upward = smoothing, slanted bands =
    traveling fronts.
    """
    field = np.asarray(field)
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(
        field,
        aspect="auto",
        origin="lower",
        extent=[x[0], x[-1], t[0], t[-1]],
        cmap=cmap,
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel("time t")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, label="amplitude")
    return fig, ax


def plot_projection(t, signal, basis, coeff, basis_label="basis", ax=None):
    """A signal, one basis wave, and the projected component ``coeff·basis``.

    Visualises "a Fourier coefficient is a projection": the red curve is how much
    of ``basis`` lives inside ``signal``.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3))
    ax.plot(t, signal, color="black", lw=1.6, label="signal f")
    ax.plot(t, basis, color="#2ca02c", lw=1.0, ls=":", label=basis_label)
    ax.plot(
        t,
        coeff * np.asarray(basis),
        color="#d62728",
        lw=2.0,
        label=f"projection = {coeff:.2f}·{basis_label}",
    )
    ax.axhline(0, color="gray", lw=0.6)
    ax.set_xlabel("x")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    return ax


def plot_window_comparison(n=128):
    """Common window shapes (left) and their log-magnitude spectra (right).

    The trade-off is visible: a narrow main lobe (resolution) versus low side
    lobes (leakage). Rectangular has the narrowest main lobe but the worst skirts.
    """
    windows = {
        "rectangular": np.ones(n),
        "Hann": np.hanning(n),
        "Hamming": np.hamming(n),
        "Blackman": np.blackman(n),
    }
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    for name, w in windows.items():
        ax[0].plot(w, label=name)
        spec = np.abs(np.fft.rfft(w, 8 * n))
        spec = 20 * np.log10(spec / spec.max() + 1e-12)
        bins = np.arange(len(spec)) / 8.0  # 8x zero-pad -> fractional original bins
        ax[1].plot(bins, spec, label=name)
    ax[0].set_title("window shapes (time)")
    ax[0].set_xlabel("sample")
    ax[0].legend(fontsize=7)
    ax[0].grid(alpha=0.25)
    ax[1].set_title("spectra (dB): main lobe vs side lobes")
    ax[1].set_xlabel("frequency [bins]")
    ax[1].set_xlim(0, 8)
    ax[1].set_ylim(-110, 5)
    ax[1].legend(fontsize=7)
    ax[1].grid(alpha=0.25)
    fig.tight_layout()
    return fig, ax


def plot_tf_tiling():
    """Heisenberg time-frequency tiles: STFT (uniform) vs wavelet (constant-Q).

    Both cover the plane, but the wavelet trades time resolution for frequency
    resolution depending on the band — fine time where it matters (high freq).
    """
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    grid = np.linspace(0, 1, 6)
    for tt in grid[:-1]:
        for ff in grid[:-1]:
            ax[0].add_patch(plt.Rectangle((tt, ff), 0.2, 0.2, fill=False, edgecolor="#1f77b4"))
    ax[0].set_title("STFT: uniform tiling")
    bands = [(0.5, 1.0, 8), (0.25, 0.5, 4), (0.125, 0.25, 2), (0.0, 0.125, 1)]
    for f0, f1, ntiles in bands:
        w = 1.0 / ntiles
        for j in range(ntiles):
            ax[1].add_patch(plt.Rectangle((j * w, f0), w, f1 - f0, fill=False, edgecolor="#d62728"))
    ax[1].set_title("wavelet: fine time at high freq")
    for a in ax:
        a.set_xlim(0, 1)
        a.set_ylim(0, 1)
        a.set_xlabel("time")
        a.set_ylabel("frequency")
        a.set_aspect("equal")
    fig.tight_layout()
    return fig, ax


def plot_convolution_slide(t, f, g, shift_fracs=(0.3, 0.5, 0.7)):
    """Convolution as flip-and-slide: at each ``t0`` show f(τ), g(t0-τ) and product.

    The shaded area under the product is ``(f*g)(t0)`` — the value the convolution
    assigns at that shift.
    """
    dt = t[1] - t[0]
    fig, ax = plt.subplots(1, len(shift_fracs), figsize=(11, 3), sharey=True)
    for a, frac in zip(ax, shift_fracs, strict=True):
        t0 = t[int(frac * len(t))]
        g_flip = np.interp(t0 - t, t, g, left=0.0, right=0.0)  # g(t0 - τ)
        prod = np.asarray(f) * g_flip
        a.plot(t, f, color="#1f77b4", lw=1.0, label="f(τ)")
        a.plot(t, g_flip, color="#2ca02c", lw=1.0, label="g(t₀-τ)")
        a.fill_between(t, prod, color="#d62728", alpha=0.4, label="product")
        a.set_title(f"t₀={t0:.2f}, (f*g)(t₀)={np.sum(prod) * dt:.2f}", fontsize=9)
        a.set_xlabel("τ")
        a.grid(alpha=0.25)
        a.legend(fontsize=7)
    fig.tight_layout()
    return fig, ax
