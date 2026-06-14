"""Heston stochastic-volatility model (A2 deep-dive — beyond Hull's local/flat vol).

    dS = r S dt + sqrt(v) S dW1
    dv = kappa (theta - v) dt + xi sqrt(v) dW2,    d<W1, W2> = rho dt.

:func:`heston_cf` is the risk-neutral characteristic function of the log-return
y = ln(S_T / S0) in the numerically stable "little trap" form (Albrecher et al.
2007). :func:`heston_mc_price` is a full-truncation Euler Monte-Carlo used to
cross-check the Fourier prices.

References: Heston (1993); Gatheral, *The Volatility Surface* Ch.2-3;
Albrecher, Mayer, Schoutens & Tistaert (2007), "The little Heston trap".
"""

from __future__ import annotations

import numpy as np


def heston_cf(u, r, T, v0, kappa, theta, xi, rho):
    """Characteristic function E[exp(i u y)] of y = ln(S_T/S0) under Q.

    Vectorized over ``u`` (returns complex). Uses the trap-stable branch so the
    complex log stays continuous for long maturities / large vol-of-vol.
    """
    u = np.asarray(u, dtype=complex)
    xi2 = xi * xi
    b = kappa - 1j * rho * xi * u
    d = np.sqrt(b * b + xi2 * (1j * u + u * u))
    g = (b - d) / (b + d)
    edt = np.exp(-d * T)
    log_term = np.log((1.0 - g * edt) / (1.0 - g))
    c = 1j * u * r * T + (kappa * theta / xi2) * ((b - d) * T - 2.0 * log_term)
    dterm = ((b - d) / xi2) * ((1.0 - edt) / (1.0 - g * edt))
    return np.exp(c + dterm * v0)


def heston_mc_price(
    S0,
    K,
    r,
    T,
    v0,
    kappa,
    theta,
    xi,
    rho,
    kind="call",
    n_steps=200,
    n_paths=100_000,
    rng=None,
):
    """Full-truncation Euler Monte-Carlo price (price, standard_error).

    Log-Euler for S given the (truncated) variance, plain Euler for v with
    v -> max(v, 0) (Lord et al. full truncation). Used to validate the Fourier
    prices independently.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    if rng is None:
        rng = np.random.default_rng(0)
    dt = T / n_steps
    sqrt_dt = np.sqrt(dt)
    corr = np.sqrt(1.0 - rho * rho)
    s = np.full(n_paths, float(S0))
    v = np.full(n_paths, float(v0))
    for _ in range(n_steps):
        z = rng.standard_normal((n_paths, 2))
        dw1 = z[:, 0] * sqrt_dt
        dw2 = (rho * z[:, 0] + corr * z[:, 1]) * sqrt_dt
        vp = np.maximum(v, 0.0)
        sqrt_vp = np.sqrt(vp)
        s *= np.exp((r - 0.5 * vp) * dt + sqrt_vp * dw1)
        v = v + kappa * (theta - vp) * dt + xi * sqrt_vp * dw2
    payoff = np.maximum(s - K, 0.0) if kind == "call" else np.maximum(K - s, 0.0)
    disc = np.exp(-r * T) * payoff
    return float(disc.mean()), float(disc.std(ddof=1) / np.sqrt(n_paths))
