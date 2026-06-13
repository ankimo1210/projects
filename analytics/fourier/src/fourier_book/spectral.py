"""Spectral (Fourier) methods for PDEs on a periodic interval ``[0, L)``.

Two facts power everything here:

* differentiation becomes multiplication by ``ik`` in Fourier space, and
* a linear, constant-coefficient evolution **decouples into independent modes**,
  so each Fourier coefficient evolves on its own (exactly, in closed form).
"""

from __future__ import annotations

import numpy as np


def wavenumbers(n: int, L: float) -> np.ndarray:
    """Angular wavenumbers ``k`` for an FFT on ``[0, L)`` with ``n`` points.

    ``k = 2π m / L`` ordered like :func:`numpy.fft.fftfreq`.
    """
    return 2 * np.pi * np.fft.fftfreq(n, d=L / n)


def spectral_derivative(u, L: float, order: int = 1) -> np.ndarray:
    """``d^order u / dx^order`` for periodic ``u`` sampled on ``[0, L)`` via FFT.

    Spectrally accurate for smooth periodic data: differentiate by multiplying
    each mode by ``(ik)^order``.
    """
    u = np.asarray(u, dtype=float)
    n = len(u)
    k = wavenumbers(n, L)
    spectrum = np.fft.fft(u)
    return np.fft.ifft((1j * k) ** order * spectrum).real


def solve_heat_spectral(u0, L: float, alpha: float, t: float) -> np.ndarray:
    """Heat equation ``u_t = alpha u_xx`` on periodic ``[0, L)``.

    Exact per mode: ``û(k, t) = û(k, 0) exp(-alpha k^2 t)``. Large ``|k|`` (high
    frequency, sharp features) decays fastest — the equation smooths.
    """
    u0 = np.asarray(u0, dtype=float)
    n = len(u0)
    k = wavenumbers(n, L)
    spectrum = np.fft.fft(u0) * np.exp(-alpha * k**2 * t)
    return np.fft.ifft(spectrum).real


def solve_wave_spectral(u0, v0, L: float, c: float, t: float) -> np.ndarray:
    """Wave equation ``u_tt = c^2 u_xx`` on periodic ``[0, L)``.

    Initial displacement ``u0`` and velocity ``v0``. Per mode with ``ω = c|k|``:
    ``û(t) = û0 cos(ω t) + v̂0 sin(ω t)/ω`` (the ``k = 0`` mode drifts as
    ``û0 + v̂0 t``).
    """
    u0 = np.asarray(u0, dtype=float)
    v0 = np.asarray(v0, dtype=float)
    n = len(u0)
    k = wavenumbers(n, L)
    w = c * np.abs(k)
    u0_hat = np.fft.fft(u0)
    v0_hat = np.fft.fft(v0)
    # sin(ω t)/ω, with the ω = 0 limit equal to t.
    sinc_term = np.where(w == 0, t, np.sin(w * t) / np.where(w == 0, 1.0, w))
    spectrum = u0_hat * np.cos(w * t) + v0_hat * sinc_term
    return np.fft.ifft(spectrum).real


def solve_poisson_spectral(f, L: float) -> np.ndarray:
    """Solve ``u'' = f`` on periodic ``[0, L)`` (``f`` must have zero mean).

    Per mode (``k != 0``): ``û = -f̂ / k^2``. The constant (``k = 0``) mode is
    free; we fix it to zero mean.
    """
    f = np.asarray(f, dtype=float)
    n = len(f)
    k = wavenumbers(n, L)
    f_hat = np.fft.fft(f)
    u_hat = np.where(k == 0, 0.0, -f_hat / np.where(k == 0, 1.0, k**2))
    return np.fft.ifft(u_hat).real
