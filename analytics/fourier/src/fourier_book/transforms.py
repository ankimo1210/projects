"""DFT / FFT helpers and numerical Fourier-series coefficients.

The fast routines wrap :mod:`numpy.fft`. The slow ``O(N^2)`` ``dft`` / ``dft_matrix``
exist so the book can *show* the matrix that the FFT computes and check that the
two agree to floating-point precision. STFT helpers wrap :mod:`scipy.signal`.
"""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------- #
# Discrete Fourier transform — the matrix view and the fast view
# --------------------------------------------------------------------------- #
def dft_matrix(n: int) -> np.ndarray:
    """``N×N`` DFT matrix ``W`` with ``W[k, j] = exp(-2πi k j / N)`` (so ``X = W @ x``)."""
    k = np.arange(n)
    return np.exp(-2j * np.pi * np.outer(k, k) / n)


def dft(x) -> np.ndarray:
    """Naive ``O(N^2)`` DFT via the matrix. Equals ``np.fft.fft(x)``."""
    x = np.asarray(x, dtype=complex)
    return dft_matrix(len(x)) @ x


def idft(spectrum) -> np.ndarray:
    """Inverse of :func:`dft`. Equals ``np.fft.ifft(spectrum)``."""
    spectrum = np.asarray(spectrum, dtype=complex)
    n = len(spectrum)
    return (np.conj(dft_matrix(n)) @ spectrum) / n


def fft_freqs(n: int, fs: float) -> np.ndarray:
    """Frequency (Hz) of each FFT bin, ordered like ``np.fft.fft`` (negatives last)."""
    return np.fft.fftfreq(n, d=1.0 / fs)


# --------------------------------------------------------------------------- #
# One-sided spectra, scaled so a pure tone reads its true amplitude / power
# --------------------------------------------------------------------------- #
def amplitude_spectrum(x, fs: float):
    """One-sided amplitude spectrum ``(freqs >= 0, amplitude)``.

    Scaled so that ``amp * sin(2π f t)`` shows a peak of height ``amp`` at ``f``
    (when ``f`` lands on a bin). DC and Nyquist are not doubled.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    spectrum = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    amp = np.abs(spectrum) * 2.0 / n
    amp[0] /= 2.0
    if n % 2 == 0:
        amp[-1] /= 2.0
    return freqs, amp


def power_spectrum(x, fs: float):
    """One-sided spectrum of **squared amplitude** ``(freqs, amplitude**2)``.

    A pure tone ``A·sin`` peaks at ``A**2`` here (this is ``amplitude_spectrum``
    squared), not the physical average power ``A**2 / 2``.
    """
    freqs, amp = amplitude_spectrum(x, fs)
    return freqs, amp**2


# --------------------------------------------------------------------------- #
# Fourier-series coefficients of a callable, computed numerically
# --------------------------------------------------------------------------- #
def fourier_series_coeffs(f, n_max: int, period: float = 2 * np.pi, n_samples: int = 4096):
    """Complex Fourier coefficients ``c_n`` for ``n`` in ``[-n_max, n_max]``.

    ``c_n = (1/T) ∫_0^T f(t) exp(-2πi n t / T) dt`` estimated by the mean over a
    uniform grid (this is the trapezoid rule for a periodic integrand).
    Returns ``(ns, c)`` with ``ns = arange(-n_max, n_max + 1)``.
    """
    t = np.linspace(0.0, period, n_samples, endpoint=False)
    ft = np.asarray(f(t), dtype=complex)
    ns = np.arange(-n_max, n_max + 1)
    basis = np.exp(-2j * np.pi * np.outer(ns, t) / period)  # (2 n_max + 1, n_samples)
    c = basis @ ft / n_samples
    return ns, c


def trig_coeffs(f, n_max: int, period: float = 2 * np.pi, n_samples: int = 4096):
    """Real trigonometric coefficients ``(a, b)`` of ``f`` over one period.

    ``f(t) ~ a[0]/2 + Σ_{n>=1} a[n] cos(2π n t/T) + b[n] sin(2π n t/T)`` with
    ``a[n] = (2/T)∫ f cos``, ``b[n] = (2/T)∫ f sin``. ``a`` has length ``n_max+1``
    (``a[0]`` is the DC term), ``b`` likewise with ``b[0] == 0``.
    """
    t = np.linspace(0.0, period, n_samples, endpoint=False)
    ft = np.asarray(f(t), dtype=float)
    a = np.zeros(n_max + 1)
    b = np.zeros(n_max + 1)
    for n in range(n_max + 1):
        ang = 2 * np.pi * n * t / period
        a[n] = 2.0 * np.mean(ft * np.cos(ang))
        b[n] = 2.0 * np.mean(ft * np.sin(ang))
    return a, b


def reconstruct_trig(a, b, t, period: float = 2 * np.pi):
    """Rebuild a signal from trig coefficients (partial sum up to ``len(a)-1``)."""
    t = np.asarray(t, dtype=float)
    out = np.full_like(t, a[0] / 2.0)
    for n in range(1, len(a)):
        ang = 2 * np.pi * n * t / period
        out = out + a[n] * np.cos(ang) + b[n] * np.sin(ang)
    return out


def reconstruct_complex(ns, c, t, period: float = 2 * np.pi):
    """Rebuild a real signal from complex coefficients ``c`` at indices ``ns``."""
    t = np.asarray(t, dtype=float)
    basis = np.exp(2j * np.pi * np.outer(ns, t) / period)  # (len(ns), len(t))
    return (np.asarray(c) @ basis).real


# --------------------------------------------------------------------------- #
# Short-time Fourier transform (time-frequency)
# --------------------------------------------------------------------------- #
def stft(x, fs: float, nperseg: int = 256, noverlap: int | None = None, window: str = "hann"):
    """Short-time Fourier transform (thin :func:`scipy.signal.stft` wrapper).

    Returns ``(freqs, times, Z)`` with complex ``Z`` of shape ``(n_freq, n_frame)``.
    """
    from scipy import signal as sps

    if noverlap is None:
        noverlap = nperseg // 2
    f, t, z = sps.stft(
        np.asarray(x, dtype=float), fs=fs, window=window, nperseg=nperseg, noverlap=noverlap
    )
    return f, t, z


def istft(z, fs: float, nperseg: int = 256, noverlap: int | None = None, window: str = "hann"):
    """Inverse STFT (thin :func:`scipy.signal.istft` wrapper). Returns the signal."""
    from scipy import signal as sps

    if noverlap is None:
        noverlap = nperseg // 2
    _, x = sps.istft(z, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap)
    return x


def spectrogram_db(
    x,
    fs: float,
    nperseg: int = 256,
    noverlap: int | None = None,
    window: str = "hann",
    floor_db: float = -80.0,
):
    """STFT magnitude in decibels, clipped to ``floor_db`` below the peak.

    Returns ``(freqs, times, S_db)`` ready for ``pcolormesh``.
    """
    f, t, z = stft(x, fs, nperseg=nperseg, noverlap=noverlap, window=window)
    s = 20.0 * np.log10(np.abs(z) + 1e-12)
    s = np.maximum(s, s.max() + floor_db)
    return f, t, s
