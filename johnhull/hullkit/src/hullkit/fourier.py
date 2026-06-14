"""Fourier option pricing: the COS method (A2 deep-dive).

Given the characteristic function of the log-return y = ln(S_T / S0) under Q,
:func:`cos_price` prices European vanillas and :func:`cos_density` recovers the
risk-neutral density — both as Fourier-cosine series. This is how stochastic-vol
models (Heston) and many others are priced when no closed form exists.

References: Fang & Oosterlee (2008), "A novel pricing method for European options
based on Fourier-cosine series expansions"; Gatheral, *The Volatility Surface*.
"""

from __future__ import annotations

import numpy as np


def lognormal_cf(r, T, sigma):
    """CF of y=ln(S_T/S0) under Black-Scholes GBM: N((r-½σ²)T, σ²T).

    A closed-form reference CF for validating the COS machinery against BSM.
    """

    def cf(u):
        u = np.asarray(u, dtype=complex)
        return np.exp(1j * u * (r - 0.5 * sigma**2) * T - 0.5 * sigma**2 * T * u * u)

    return cf


def _cumulants(cf, h=1e-4):
    """First two cumulants (mean, variance) of y via finite differences of ln cf."""
    psi_p = np.log(cf(np.array([h])))[0]
    psi_m = np.log(cf(np.array([-h])))[0]
    c1 = ((psi_p - psi_m) / (2.0 * h)).imag
    c2 = (-(psi_p + psi_m) / (h * h)).real  # ln cf(0)=0, so ψ(h)-2ψ(0)+ψ(-h)=ψ(h)+ψ(-h)
    return c1, c2


def _chi_psi(k, a, b, c, d):
    """Fang-Oosterlee χ_k and ψ_k integrals on [c,d] (cosine basis on [a,b])."""
    omega = k * np.pi / (b - a)
    psi = np.empty_like(omega)
    psi[0] = d - c
    psi[1:] = (np.sin(omega[1:] * (d - a)) - np.sin(omega[1:] * (c - a))) / omega[1:]
    chi = (1.0 / (1.0 + omega**2)) * (
        np.cos(omega * (d - a)) * np.exp(d)
        - np.cos(omega * (c - a)) * np.exp(c)
        + omega * np.sin(omega * (d - a)) * np.exp(d)
        - omega * np.sin(omega * (c - a)) * np.exp(c)
    )
    return chi, psi


def cos_price(cf, S0, K, r, T, kind="call", N=256, L=12.0, cumulants=None):
    """Price a European option by the COS method.

    ``cf`` is a callable ``u -> E[exp(i u y)]`` for the log-return y=ln(S_T/S0)
    under Q. ``N`` cosine terms, truncation range set by ``L`` standard deviations.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    c1, c2 = cumulants if cumulants is not None else _cumulants(cf)
    half = L * np.sqrt(abs(c2))
    a, b = c1 - half, c1 + half
    k = np.arange(N)
    omega = k * np.pi / (b - a)
    fk = np.real(cf(omega) * np.exp(-1j * omega * a))
    if kind == "call":
        lo, hi = max(np.log(K / S0), a), b
        chi, psi = _chi_psi(k, a, b, lo, hi)
        uk = (2.0 / (b - a)) * (S0 * chi - K * psi)
    else:
        lo, hi = a, min(np.log(K / S0), b)
        chi, psi = _chi_psi(k, a, b, lo, hi)
        uk = (2.0 / (b - a)) * (K * psi - S0 * chi)
    weights = np.ones(N)
    weights[0] = 0.5
    return float(np.exp(-r * T) * np.sum(weights * fk * uk))


def cos_density(cf, N=256, L=12.0, n_grid=400, cumulants=None):
    """Recover the density of y=ln(S_T/S0) from its CF via COS. Returns (y, f)."""
    c1, c2 = cumulants if cumulants is not None else _cumulants(cf)
    half = L * np.sqrt(abs(c2))
    a, b = c1 - half, c1 + half
    k = np.arange(N)
    omega = k * np.pi / (b - a)
    ak = (2.0 / (b - a)) * np.real(cf(omega) * np.exp(-1j * omega * a))
    ak[0] *= 0.5
    y = np.linspace(a, b, n_grid)
    cos_mat = np.cos(np.outer(y - a, omega))  # (n_grid, N)
    f = cos_mat @ ak
    return y, f
