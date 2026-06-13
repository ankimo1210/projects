"""Synthetic, download-free sample data.

Everything here is generated from code with a fixed seed, so the notebooks run
identically offline. Functions that could use real data expose a ``path`` hook
("bring your own data") but never require it.
"""

from __future__ import annotations

import numpy as np

from . import signals


def make_multitone(
    fs=1000.0, duration=1.0, freqs=(5.0, 12.0, 30.0), amps=(1.0, 0.5, 0.3), snr_db=None, seed=0
):
    """Sum of pure tones, optionally with white noise at a target SNR.

    Returns ``(t, x)``. The clean spectrum is a few sharp lines — the simplest
    thing for which the amplitude spectrum should read back the input ``amps``.
    """
    t, _ = signals.time_grid(duration, fs)
    # Pure sine tones, so the amplitude spectrum reads back `amps` at `freqs`.
    x = signals.harmonic_sum(t, np.asarray(freqs), np.asarray(amps), phases=np.zeros(len(freqs)))
    if snr_db is not None:
        x = signals.add_noise(x, snr_db, seed=seed)
    return t, x


def make_chirp(fs=2000.0, duration=2.0, f0=20.0, f1=400.0, snr_db=None, seed=0):
    """Linear-frequency sweep — a textbook non-stationary signal for STFT."""
    t, _ = signals.time_grid(duration, fs)
    x = signals.chirp(t, f0, f1, duration=duration)
    if snr_db is not None:
        x = signals.add_noise(x, snr_db, seed=seed)
    return t, x


def make_two_tone_burst(fs=2000.0, duration=2.0, f_low=40.0, f_high=300.0, seed=0):
    """Low tone in the first half, high tone in the second half.

    The plain FFT sees both tones but not *when* they occur; the spectrogram does.
    """
    t, _ = signals.time_grid(duration, fs)
    half = t < (t[0] + duration / 2)
    x = np.where(half, signals.sine(t, f_low), signals.sine(t, f_high))
    return t, x


def make_test_image(n=128):
    """Synthetic grayscale image with clear 2-D frequency content.

    Diagonal sinusoidal stripes (a single dominant spatial frequency) plus a
    smooth Gaussian blob. Its 2-D FFT shows a symmetric pair of bright peaks on
    a low-frequency core — ideal for the image notebook (09).
    """
    x = np.linspace(0, 1, n)
    y = np.linspace(0, 1, n)
    xx, yy = np.meshgrid(x, y)
    stripes = np.sin(2 * np.pi * 12 * (xx + yy))  # diagonal grating
    blob = np.exp(-((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / (2 * 0.05))
    img = 0.6 * stripes + 1.2 * blob
    img = (img - img.min()) / (img.max() - img.min())  # -> [0, 1]
    return img


def load_price_series(path=None, n=1024, seed=0):
    """A finance-like daily series: random-walk log price + a weak weekly cycle.

    With ``path`` given, reads a CSV and returns its ``close`` column (or the
    first numeric column) instead — the bring-your-own-data hook. The synthetic
    default deliberately mixes a real trend (random walk) with a faint periodic
    component, to practise telling a genuine cycle from spectral noise (09).
    """
    if path is not None:
        import pandas as pd

        df = pd.read_csv(path)
        col = "close" if "close" in df.columns else df.select_dtypes("number").columns[0]
        return np.asarray(df[col], dtype=float)

    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 1.0, size=n)
    log_price = np.cumsum(steps) * 0.01
    day = np.arange(n)
    weekly = 0.02 * np.sin(2 * np.pi * day / 5.0)  # faint 5-day cycle
    return 100.0 * np.exp(log_price + weekly)
