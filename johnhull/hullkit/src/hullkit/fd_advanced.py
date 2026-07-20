"""Explicit finite-difference scheme and its (conditional) stability (A3 deep-dive).

Complements :mod:`hullkit.fd` (implicit / Crank-Nicolson, unconditionally stable)
with the *explicit* theta=0 scheme, which is only stable when the von-Neumann factor
sigma^2 dt / dx^2 is small enough — the textbook reason practitioners use implicit
or Crank-Nicolson. References: Wilmott; Duffy, *Finite Difference Methods in
Financial Engineering*.
"""

from __future__ import annotations

import numpy as np

from .fd import _log_price_grid


def fd_explicit(S0, K, r, sigma, T, q=0.0, kind="call", n_s=100, n_t=4000, s_max_mult=4.0):
    """Explicit (forward-Euler) FD price on a uniform ln-S grid.

    Stable defaults (``n_t`` large relative to ``n_s``). Coarsen the time grid
    (small ``n_t``) and the scheme blows up — see :func:`stability_factor`.
    As in :func:`hullkit.fd.fd_vanilla`, ``n_s`` is a minimum: the domain and
    interval count expand for distant strikes or wide diffusion ranges.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    if T <= 0.0 or sigma <= 0.0 or n_t < 1:
        raise ValueError("T, sigma, and n_t must be > 0")
    x = _log_price_grid(S0, K, sigma, T, n_s, s_max_mult)
    s_grid = np.exp(x)
    dx = x[1] - x[0]
    dt = T / n_t
    drift = r - q - 0.5 * sigma**2
    a = 0.5 * sigma**2 / dx**2
    b = drift / (2.0 * dx)
    lo = dt * (a - b)
    di = 1.0 + dt * (-2.0 * a - r)
    up = dt * (a + b)
    f = np.maximum(s_grid - K, 0.0) if kind == "call" else np.maximum(K - s_grid, 0.0)
    for step in range(1, n_t + 1):
        tau = step * dt
        new = f.copy()
        new[1:-1] = lo * f[:-2] + di * f[1:-1] + up * f[2:]
        if kind == "call":
            new[0] = 0.0
            new[-1] = max(s_grid[-1] * np.exp(-q * tau) - K * np.exp(-r * tau), 0.0)
        else:
            new[0] = max(K * np.exp(-r * tau) - s_grid[0] * np.exp(-q * tau), 0.0)
            new[-1] = 0.0
        f = new
    return float(np.interp(np.log(S0), x, f))


def stability_factor(sigma, n_s, n_t, s_max_mult=4.0):
    """von-Neumann amplification factor sigma^2 dt / dx^2 (per unit T).

    The explicit scheme is stable when this is below ~0.5; above it, errors grow.
    """
    dx = 2.0 * np.log(s_max_mult) / n_s
    dt = 1.0 / n_t
    return float(sigma**2 * dt / dx**2)
