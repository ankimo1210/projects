"""Synthetic time-domain signals used as inputs and test functions.

Everything here is generated in code (no external data) and any randomness is
seeded, so the notebooks and tests are reproducible. These are the f(t) we push
through transforms and systems.
"""

from __future__ import annotations

import numpy as np


def time_grid(t_max: float = 10.0, n: int = 500) -> np.ndarray:
    """Uniform time grid t in [0, t_max] (n samples), starting at 0."""
    return np.linspace(0.0, t_max, n)


def unit_step(t, t0: float = 0.0) -> np.ndarray:
    """Heaviside step u(t - t0): 0 before t0, 1 after."""
    return (np.asarray(t, dtype=float) >= t0).astype(float)


def impulse_approx(t, t0: float = 0.0, width: float = 0.05) -> np.ndarray:
    """Narrow Gaussian bump of unit area -- a usable stand-in for delta(t - t0)."""
    t = np.asarray(t, dtype=float)
    g = np.exp(-0.5 * ((t - t0) / width) ** 2)
    area = np.trapezoid(g, t) if hasattr(np, "trapezoid") else np.trapz(g, t)
    return g / area if area > 0 else g


def decaying_exponential(t, a: float = 1.0) -> np.ndarray:
    """e^{-a t} for t >= 0 -- the prototypical decaying signal."""
    return np.exp(-a * np.asarray(t, dtype=float))


def damped_sine(t, sigma: float = -0.5, omega: float = 4.0) -> np.ndarray:
    """e^{sigma t} sin(omega t): growth/decay (sigma) times oscillation (omega)."""
    t = np.asarray(t, dtype=float)
    return np.exp(sigma * t) * np.sin(omega * t)


def sinusoid(t, omega: float = 2.0, phase: float = 0.0) -> np.ndarray:
    """Pure sinusoid cos(omega t + phase)."""
    return np.cos(omega * np.asarray(t, dtype=float) + phase)


def square_wave(t, period: float = 2.0, duty: float = 0.5) -> np.ndarray:
    """Unit square wave with the given period and duty cycle (in [0, 1])."""
    frac = np.mod(np.asarray(t, dtype=float), period) / period
    return (frac < duty).astype(float)


def noisy_signal(t, sigma: float = -0.3, omega: float = 3.0, noise: float = 0.05, seed: int = 0):
    """A damped sine plus small Gaussian noise (seeded) -- a 'measured' signal."""
    rng = np.random.default_rng(seed)
    clean = damped_sine(t, sigma, omega)
    return clean + noise * rng.standard_normal(np.shape(clean))
