"""Private Hull §33.1 HJM bond/forward identities and deterministic-vol paths.

The forward diffusion is sigma=-partial_T v, with signed bond diffusion v.
A finite Brownian factor count does not imply a scalar Markov short rate.
The batched simulator below is explicitly restricted to deterministic vol;
per-path drift/step functions can also use an adapted history-bound callback.
"""

from itertools import pairwise

import numpy as np
from scipy.integrate import quad_vec


def _rho(size, correlation):
    rho = np.eye(size) if correlation is None else np.asarray(correlation, dtype=float)
    if (
        rho.shape != (size, size)
        or not np.allclose(rho, rho.T, atol=1e-12)
        or not np.allclose(np.diag(rho), 1, atol=1e-12)
        or np.linalg.eigvalsh(rho).min() < -1e-12
    ):
        raise ValueError("positive semidefinite correlation with unit diagonal required")
    return rho


def bond_diffusion(time, maturity, volatility):
    """v(t,T)=-integral_t^T sigma(t,u)du, so v(t,t)=0."""
    if time < 0 or maturity < time:
        raise ValueError("nonnegative time and future maturity required")
    return -np.asarray(
        quad_vec(
            lambda u: np.asarray(volatility(time, u), dtype=float), time, maturity, epsabs=1e-13
        )[0]
    )


def hjm_forward_drift(time, maturity, volatility, *, correlation=None):
    """Risk-neutral sigma(t,T)' rho integral_t^T sigma(t,u)du."""
    sigma = np.atleast_1d(volatility(time, maturity)).astype(float)
    return float(
        -sigma
        @ _rho(sigma.size, correlation)
        @ np.atleast_1d(bond_diffusion(time, maturity, volatility))
    )


def finite_forward_sde(time, start, end, volatility, *, correlation=None):
    """SDE of log[P(t,start)/P(t,end)]/(end-start); continuous forward units."""
    if end <= start or start < time:
        raise ValueError("ordered future forward interval required")
    v0 = np.atleast_1d(bond_diffusion(time, start, volatility))
    v1 = np.atleast_1d(bond_diffusion(time, end, volatility))
    rho = _rho(v0.size, correlation)
    delta = end - start
    return dict(
        drift=float((v1 @ rho @ v1 - v0 @ rho @ v0) / (2 * delta)), diffusion=(v0 - v1) / delta
    )


def hjm_forward_step(
    forwards, time, maturities, delta, brownian_increment, volatility, *, correlation=None
):
    """Euler step with covariance-rho Brownian increment, no rate clipping."""
    f, T = np.asarray(forwards, dtype=float), np.asarray(maturities, dtype=float)
    dW = np.atleast_1d(brownian_increment)
    if delta <= 0 or f.shape != T.shape or T.ndim != 1 or np.any(T < time):
        raise ValueError("positive time step and matching future forward vector required")
    loadings = np.array([np.atleast_1d(volatility(time, u)) for u in T])
    if loadings.shape[1] != dW.size:
        raise ValueError("factor increment dimension must match vol")
    mu = np.array([hjm_forward_drift(time, u, volatility, correlation=correlation) for u in T])
    return f + mu * delta + loadings @ dW


def simulate_hjm(
    times, maturities, initial_forwards, volatility, samples, rng, *, correlation=None
):
    """Fixed-maturity HJM Euler paths with left-time money-market discount.

    Every time node must appear on the maturity grid to observe the short
    rate without extrapolation. Terminal bond reconstruction is a separate
    maturity quadrature. Expired forwards are retained but never evolved.
    History-dependent vol needs a per-path callback/step; it is not batched
    by this deterministic-vol routine.
    """
    ts, T = np.asarray(times, dtype=float), np.asarray(maturities, dtype=float)
    f0 = np.asarray(initial_forwards, dtype=float)
    if (
        ts.ndim != 1
        or ts.size < 2
        or ts[0] != 0
        or np.any(np.diff(ts) <= 0)
        or T.ndim != 1
        or f0.shape != T.shape
        or np.any(np.diff(T) <= 0)
        or samples < 1
    ):
        raise ValueError(
            "increasing times from zero, maturity grid/forwards and positive samples required"
        )
    indices = [int(np.argmin(abs(T - t))) for t in ts]
    if any(abs(T[i] - t) > 1e-10 for i, t in zip(indices, ts, strict=True)):
        raise ValueError("each short-rate observation time must be a maturity node")
    size = np.atleast_1d(volatility(0, T[-1])).size
    rho = _rho(size, correlation)
    ev, vec = np.linalg.eigh(rho)
    root = vec * np.sqrt(np.maximum(ev, 0))
    forwards = np.tile(f0, (samples, 1))
    rates = np.empty((samples, ts.size))
    rates[:, 0] = f0[indices[0]]
    discounts = np.ones(samples)
    for i, (lo, hi) in enumerate(pairwise(ts)):
        dt = hi - lo
        alive = T >= lo - 1e-12
        loads = np.array([np.atleast_1d(volatility(lo, U)) for U in T[alive]])
        drift = np.array([hjm_forward_drift(lo, U, volatility, correlation=rho) for U in T[alive]])
        increments = rng.standard_normal((samples, size)) @ root.T * np.sqrt(dt)
        discounts *= np.exp(-rates[:, i] * dt)
        forwards[:, alive] += drift * dt + increments @ loads.T
        rates[:, i + 1] = forwards[:, indices[i + 1]]
    return dict(
        terminal_forwards=forwards,
        short_rate_paths=rates,
        discounts=discounts,
        times=ts,
        maturities=T,
    )


def hjm_history_noise(current_time, history_times, increments, volatility, *, maturity_bump=1e-5):
    """Left-history stochastic contributions to r(t) and its maturity slope.

    Equal rate noise with different slope noise demonstrates why one Brownian
    factor need not supply a scalar Markov rate. Deterministic mean terms are
    excluded; the given history increments must already be observed.
    """
    times = np.asarray(history_times, dtype=float)
    dw = np.asarray(increments, dtype=float)
    if (
        times.ndim != 1
        or dw.ndim != 2
        or dw.shape[0] != times.size
        or np.any(times < 0)
        or np.any(times > current_time)
        or maturity_bump <= 0
    ):
        raise ValueError(
            "observed nonnegative history times and matching factor increments required"
        )
    rate = slope = 0.0
    for t, d in zip(times, dw, strict=True):
        sigma = np.atleast_1d(volatility(t, current_time))
        derivative = (
            np.atleast_1d(volatility(t, current_time + maturity_bump)) - sigma
        ) / maturity_bump
        rate += float(sigma @ d)
        slope += float(derivative @ d)
    return dict(rate_noise=rate, maturity_slope_noise=slope)
