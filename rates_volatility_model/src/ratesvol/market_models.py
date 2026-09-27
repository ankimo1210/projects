"""HJM (one factor, fixed-maturity grid) and the LIBOR/forward market model under the spot measure."""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------- HJM
def hjm_drift(t, T_grid, vol_func, n_quad=33):
    """No-arbitrage drift alpha(t,T) = sigma(t,T) * integral_t^T sigma(t,u) du; zero for T <= t.

    ``vol_func(t, u)`` must accept an array ``u`` (a scalar return is broadcast).
    """
    T_grid = np.asarray(T_grid, dtype=float)
    sig_T = np.broadcast_to(vol_func(t, T_grid), T_grid.shape)
    alpha = np.zeros_like(T_grid)
    for j, T in enumerate(T_grid):
        if T <= t:
            continue
        u = np.linspace(t, T, n_quad)
        alpha[j] = sig_T[j] * np.trapezoid(np.broadcast_to(vol_func(t, u), u.shape), u)
    return alpha


def hjm_simulate(T_grid, f0, vol_func, t_grid, n_paths, rng):
    """Euler simulation of df(t,T) = alpha dt + sigma dW for every T on ``T_grid``.

    Forwards with T <= t are frozen. Returns (n_paths, len(t_grid), len(T_grid)).
    """
    T_grid = np.asarray(T_grid, dtype=float)
    t_grid = np.asarray(t_grid, dtype=float)
    out = np.empty((n_paths, len(t_grid), len(T_grid)))
    out[:, 0, :] = np.asarray(f0, dtype=float)
    for i in range(1, len(t_grid)):
        t, dt = t_grid[i - 1], t_grid[i] - t_grid[i - 1]
        alive = T_grid > t
        sig = np.broadcast_to(vol_func(t, T_grid), T_grid.shape) * alive
        alpha = hjm_drift(t, T_grid, vol_func)
        dW = np.sqrt(dt) * rng.standard_normal(n_paths)
        out[:, i, :] = out[:, i - 1, :] + alpha * dt + dW[:, None] * sig[None, :]
    return out


# --------------------------------------------------------------------- LMM
def lmm_simulate_spot(tenor_dates, L0, vols, corr, steps_per_period, n_paths, rng):
    """Log-Euler LMM under the spot (rolling) measure.

    ``tenor_dates`` = T_0=0 < T_1 < ... < T_N; forward L_i accrues over [T_i, T_{i+1}] and
    fixes at T_i. Drift for alive i >= eta(t): mu_i = sigma_i sum_{j=eta(t)}^{i}
    tau_j rho_ij sigma_j L_j / (1 + tau_j L_j)  (Glasserman 2003, eq. 3.112).

    Returns (times, L) with L of shape (n_paths, len(times), N); forwards are frozen after
    their fixing date.
    """
    T = np.asarray(tenor_dates, dtype=float)
    L0 = np.asarray(L0, dtype=float)
    vols = np.asarray(vols, dtype=float)
    N = len(L0)
    if len(T) != N + 1:
        raise ValueError("need len(tenor_dates) == len(L0) + 1")
    tau = np.diff(T)
    chol = np.linalg.cholesky(corr)
    times = [0.0]
    for k in range(N):
        times.extend(np.linspace(T[k], T[k + 1], steps_per_period + 1)[1:])
    times = np.array(times)
    L = np.empty((n_paths, len(times), N))
    L[:, 0, :] = L0
    for s in range(1, len(times)):
        t, dt = times[s - 1], times[s] - times[s - 1]
        eta = int(np.searchsorted(T, t, side="right"))  # first forward not yet fixed
        cur = L[:, s - 1, :].copy()
        dW = (rng.standard_normal((n_paths, N)) @ chol.T) * np.sqrt(dt)
        new = cur.copy()
        for i in range(eta, N):
            j = np.arange(eta, i + 1)
            w = tau[j] * cur[:, j] / (1 + tau[j] * cur[:, j])
            mu = vols[i] * (w * (corr[i, j] * vols[j])).sum(axis=1)
            new[:, i] = cur[:, i] * np.exp((mu - 0.5 * vols[i] ** 2) * dt + vols[i] * dW[:, i])
        L[:, s, :] = new
    return times, L


def lmm_fixings(times, L, tenor_dates):
    """L_i(T_i) for each forward: array (n_paths, N)."""
    T = np.asarray(tenor_dates, dtype=float)
    idx = [int(np.argmin(np.abs(times - T[i]))) for i in range(L.shape[2])]
    return np.stack([L[:, idx[i], i] for i in range(L.shape[2])], axis=1)


def spot_numeraire(fixings, tenor_dates):
    """B(T_n) = prod_{j<n} (1 + tau_j L_j(T_j)) for n = 1..N: array (n_paths, N)."""
    tau = np.diff(np.asarray(tenor_dates, dtype=float))
    return np.cumprod(1 + tau * fixings, axis=1)
