"""Interactive ipywidgets demos.

The ``ipywidgets`` import is guarded so the module imports anywhere. Each demo
needs a live JupyterLab kernel to be interactive; in a static build the
notebooks render an equivalent static figure right beside the widget, so the
idea survives without interactivity.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from . import filters, signals, transforms


def _require_widgets():
    try:
        import ipywidgets
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "ipywidgets is not available — run this inside JupyterLab to use the "
            "interactive demo (the notebook also shows a static version)."
        ) from exc
    return ipywidgets


def interactive_sine(fs=500.0, duration=1.0):
    """Sliders for amplitude, frequency and phase of a single sine wave."""
    w = _require_widgets()
    t, _ = signals.time_grid(duration, fs)

    def _draw(amp=1.0, freq=3.0, phase=0.0):
        plt.figure(figsize=(8, 3))
        plt.plot(t, signals.sine(t, freq, amp, phase), color="#1f77b4")
        plt.axhline(0, color="gray", lw=0.6)
        plt.ylim(-3, 3)
        plt.title(f"amp={amp:.2f}, freq={freq:.2f} Hz, phase={phase:.2f} rad")
        plt.xlabel("time t [s]")
        plt.grid(alpha=0.25)
        plt.show()

    return w.interact(
        _draw,
        amp=w.FloatSlider(min=0.0, max=3.0, step=0.1, value=1.0),
        freq=w.FloatSlider(min=0.5, max=20.0, step=0.5, value=3.0),
        phase=w.FloatSlider(min=0.0, max=2 * np.pi, step=0.1, value=0.0),
    )


def interactive_wave_sum(fs=500.0, duration=1.0):
    """Add up to three harmonics and watch the resulting waveform."""
    w = _require_widgets()
    t, _ = signals.time_grid(duration, fs)

    def _draw(a1=1.0, a2=0.0, a3=0.0):
        comps = [signals.sine(t, 1, a1), signals.sine(t, 2, a2), signals.sine(t, 3, a3)]
        plt.figure(figsize=(8, 3))
        plt.plot(t, np.sum(comps, axis=0), color="black", lw=1.8)
        plt.axhline(0, color="gray", lw=0.6)
        plt.ylim(-3, 3)
        plt.title(f"a1·sin(2πt) + a2·sin(4πt) + a3·sin(6πt), a=({a1:.1f},{a2:.1f},{a3:.1f})")
        plt.xlabel("time t [s]")
        plt.grid(alpha=0.25)
        plt.show()

    return w.interact(
        _draw,
        a1=w.FloatSlider(min=-1.5, max=1.5, step=0.1, value=1.0),
        a2=w.FloatSlider(min=-1.5, max=1.5, step=0.1, value=0.0),
        a3=w.FloatSlider(min=-1.5, max=1.5, step=0.1, value=0.0),
    )


def interactive_square_partial_sum(fs=2000.0, duration=1.0, freq=3.0):
    """Slide the number of odd harmonics; watch the square wave (and Gibbs) form."""
    w = _require_widgets()
    t, _ = signals.time_grid(duration, fs)
    target = signals.square_wave(t, freq)

    def _draw(n_terms=1):
        approx = signals.square_wave_partial_sum(t, freq, n_terms)
        plt.figure(figsize=(8, 3))
        plt.plot(t, target, color="gray", lw=1.0, label="square wave")
        plt.plot(t, approx, color="#d62728", lw=1.5, label=f"N = {n_terms}")
        plt.ylim(-1.6, 1.6)
        plt.title(f"odd-harmonic partial sum, N = {n_terms}")
        plt.xlabel("time t [s]")
        plt.legend(loc="upper right", fontsize=8)
        plt.grid(alpha=0.25)
        plt.show()

    return w.interact(_draw, n_terms=w.IntSlider(min=1, max=40, step=1, value=1))


def interactive_lowpass(fs=1000.0, duration=1.0):
    """A noisy multitone with a low-pass cutoff slider (time + spectrum)."""
    w = _require_widgets()
    t, _ = signals.time_grid(duration, fs)
    clean = signals.harmonic_sum(t, [5, 12, 40], [1.0, 0.7, 0.4])
    noisy = signals.add_noise(clean, snr_db=5.0, seed=0)

    def _draw(cutoff=50.0):
        y = filters.lowpass(noisy, fs, cutoff)
        freqs, amp = transforms.amplitude_spectrum(y, fs)
        _, ax = plt.subplots(1, 2, figsize=(11, 3))
        ax[0].plot(t, noisy, color="lightgray", lw=0.8, label="noisy")
        ax[0].plot(t, y, color="#1f77b4", lw=1.4, label="filtered")
        ax[0].set_title(f"low-pass, cutoff = {cutoff:.0f} Hz")
        ax[0].set_xlabel("time t [s]")
        ax[0].legend(fontsize=8)
        ax[0].grid(alpha=0.25)
        ax[1].plot(freqs, amp, color="#d62728")
        ax[1].axvline(cutoff, color="black", ls="--", lw=1)
        ax[1].set_xlim(0, 100)
        ax[1].set_title("amplitude spectrum")
        ax[1].set_xlabel("frequency f [Hz]")
        ax[1].grid(alpha=0.25)
        plt.show()

    return w.interact(_draw, cutoff=w.FloatSlider(min=5.0, max=100.0, step=5.0, value=50.0))
