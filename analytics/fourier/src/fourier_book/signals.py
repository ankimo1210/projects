"""Signal generators: pure tones, complex exponentials, classic periodic waves.

These are the atoms of the book. A Fourier series or transform is, in the end,
a comparison of a signal against these building blocks. Frequencies are in
hertz, time in seconds, angles in radians.
"""

from __future__ import annotations

import numpy as np


def time_grid(duration: float, fs: float):
    """Uniform sample grid of ``duration`` seconds at ``fs`` Hz.

    Returns ``(t, dt)``. The grid has ``N = round(duration * fs)`` points and
    omits the right endpoint (``t[-1] == duration - dt``), which keeps periodic
    signals seamless for the DFT.
    """
    n = round(duration * fs)
    t = np.arange(n) / fs
    return t, 1.0 / fs


def sine(t, freq, amp=1.0, phase=0.0):
    """``amp * sin(2π f t + phase)``."""
    return amp * np.sin(2 * np.pi * freq * np.asarray(t, dtype=float) + phase)


def cosine(t, freq, amp=1.0, phase=0.0):
    """``amp * cos(2π f t + phase)``."""
    return amp * np.cos(2 * np.pi * freq * np.asarray(t, dtype=float) + phase)


def complex_exponential(t, freq):
    """``exp(2πi f t)`` — the rotating phasor. Magnitude is exactly 1 everywhere."""
    return np.exp(2j * np.pi * freq * np.asarray(t, dtype=float))


def harmonic_sum(t, freqs, amps=None, phases=None):
    """Sum of sinusoids: ``Σ_k amp_k sin(2π f_k t + φ_k)``.

    The canonical "many simple waves add up to a complex one" picture.
    """
    t = np.asarray(t, dtype=float)
    freqs = np.atleast_1d(freqs)
    if amps is None:
        amps = np.ones_like(freqs, dtype=float)
    if phases is None:
        phases = np.zeros_like(freqs, dtype=float)
    out = np.zeros_like(t)
    for f, a, p in zip(freqs, amps, phases, strict=True):
        out = out + a * np.sin(2 * np.pi * f * t + p)
    return out


def _phase(t, freq):
    return np.asarray(t, dtype=float) * freq


def square_wave(t, freq, amp=1.0):
    """``±amp`` square wave of period ``1/freq`` (sign of a sine)."""
    return amp * np.sign(np.sin(2 * np.pi * freq * np.asarray(t, dtype=float)))


def sawtooth_wave(t, freq, amp=1.0):
    """Rising sawtooth in ``[-amp, amp)``, period ``1/freq``."""
    ph = _phase(t, freq)
    return amp * (2.0 * (ph - np.floor(ph + 0.5)))


def triangle_wave(t, freq, amp=1.0):
    """Triangle wave in ``[-amp, amp]``, period ``1/freq``."""
    ph = _phase(t, freq)
    return amp * (2.0 * np.abs(2.0 * (ph - np.floor(ph + 0.5))) - 1.0)


def square_wave_partial_sum(t, freq, n_terms, amp=1.0):
    """Odd-harmonic Fourier partial sum of a square wave.

    ``(4 amp/π) Σ_{k=1,3,5,...} sin(2π k f t) / k`` using ``n_terms`` odd
    harmonics. Used to *show* Gibbs overshoot near the jumps.
    """
    t = np.asarray(t, dtype=float)
    out = np.zeros_like(t)
    for i in range(n_terms):
        k = 2 * i + 1
        out = out + np.sin(2 * np.pi * k * freq * t) / k
    return (4.0 * amp / np.pi) * out


def chirp(t, f0, f1, duration=None, amp=1.0):
    """Linear chirp sweeping instantaneous frequency ``f0 -> f1``.

    If ``duration`` is None the sweep spans ``t[0]..t[-1]``. The instantaneous
    frequency grows linearly, so the spectrogram (notebook 07) is a slanted line.
    """
    t = np.asarray(t, dtype=float)
    if duration is None:
        duration = t[-1] - t[0] if t.size > 1 else 1.0
    rate = (f1 - f0) / duration
    phase = 2 * np.pi * (f0 * t + 0.5 * rate * t * t)
    return amp * np.sin(phase)


def gaussian_pulse(t, t0=0.0, width=1.0, amp=1.0):
    """Gaussian envelope ``amp * exp(-((t-t0)/width)^2 / 2)``.

    Its Fourier transform is again a Gaussian — the textbook example for the
    time/frequency width trade-off (uncertainty).
    """
    t = np.asarray(t, dtype=float)
    return amp * np.exp(-0.5 * ((t - t0) / width) ** 2)


def add_noise(x, snr_db, seed=0):
    """Add white Gaussian noise at a target signal-to-noise ratio (dB).

    Reproducible given ``seed``. SNR in dB is ``10 log10(P_signal / P_noise)``.
    """
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    p_signal = np.mean(x**2)
    p_noise = p_signal / (10.0 ** (snr_db / 10.0))
    noise = rng.normal(0.0, np.sqrt(p_noise), size=x.shape)
    return x + noise
