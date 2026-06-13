"""Frequency-domain filtering and convolution.

A *filter* keeps or removes components by frequency; *convolution* mixes a
signal with its neighbours through a kernel. The convolution theorem ties the
two together: convolving in time is multiplying in frequency.
"""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------- #
# Ideal frequency masks (brick-wall) and the filtering they define
# --------------------------------------------------------------------------- #
def lowpass_mask(freqs, cutoff):
    """1 where ``|freq| <= cutoff`` else 0 — keep the slow, drop the fast."""
    return (np.abs(freqs) <= cutoff).astype(float)


def highpass_mask(freqs, cutoff):
    """1 where ``|freq| >= cutoff`` else 0 — keep the fast, drop the slow."""
    return (np.abs(freqs) >= cutoff).astype(float)


def bandpass_mask(freqs, low, high):
    """1 where ``low <= |freq| <= high`` else 0 — keep a band."""
    a = np.abs(freqs)
    return ((a >= low) & (a <= high)).astype(float)


def apply_frequency_mask(x, fs, mask):
    """Filter ``x`` by a frequency-domain mask: ``ifft(mask * fft(x))``.

    ``mask`` is either an array aligned with ``np.fft.fftfreq`` or a callable
    ``freqs -> weights``. Real input gives real output.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    spectrum = np.fft.fft(x)
    freqs = np.fft.fftfreq(n, d=1.0 / fs)
    m = mask(freqs) if callable(mask) else np.asarray(mask)
    return np.fft.ifft(spectrum * m).real


def lowpass(x, fs, cutoff):
    """Ideal low-pass filter (keep ``|f| <= cutoff``)."""
    return apply_frequency_mask(x, fs, lambda f: lowpass_mask(f, cutoff))


def highpass(x, fs, cutoff):
    """Ideal high-pass filter (keep ``|f| >= cutoff``)."""
    return apply_frequency_mask(x, fs, lambda f: highpass_mask(f, cutoff))


def bandpass(x, fs, low, high):
    """Ideal band-pass filter (keep ``low <= |f| <= high``)."""
    return apply_frequency_mask(x, fs, lambda f: bandpass_mask(f, low, high))


# --------------------------------------------------------------------------- #
# Convolution — mixing each value with its neighbours
# --------------------------------------------------------------------------- #
def convolve(x, h, mode: str = "full"):
    """Linear convolution (wraps :func:`numpy.convolve`)."""
    return np.convolve(np.asarray(x, dtype=float), np.asarray(h, dtype=float), mode=mode)


def circular_convolve(x, h):
    """Circular convolution via the FFT — the product the DFT diagonalises.

    Satisfies the convolution theorem exactly:
    ``fft(circular_convolve(x, h)) == fft(x) * fft(h)``.
    """
    x = np.asarray(x, dtype=float)
    h = np.asarray(h, dtype=float)
    n = len(x)
    return np.fft.ifft(np.fft.fft(x) * np.fft.fft(h, n)).real


def gaussian_kernel(size: int, sigma: float) -> np.ndarray:
    """Normalised 1-D Gaussian smoothing kernel of length ``size`` (sums to 1)."""
    half = (size - 1) / 2.0
    k = np.arange(size) - half
    w = np.exp(-0.5 * (k / sigma) ** 2)
    return w / w.sum()


def moving_average(x, k: int):
    """Length-``k`` moving average — convolution with a normalised box kernel."""
    kernel = np.ones(k) / k
    return convolve(x, kernel, mode="same")


def smooth_gaussian(x, sigma: float, size: int | None = None):
    """Smooth ``x`` by convolving with a Gaussian kernel (edge-padded)."""
    if size is None:
        size = int(2 * np.ceil(3 * sigma) + 1)
    size = int(size)
    if size % 2 == 0:
        size += 1  # force odd so the centered 'valid' convolution preserves length
    kernel = gaussian_kernel(size, sigma)
    pad = size // 2
    xp = np.pad(np.asarray(x, dtype=float), pad, mode="edge")
    return np.convolve(xp, kernel, mode="valid")
