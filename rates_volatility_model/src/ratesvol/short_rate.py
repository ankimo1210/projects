"""Short-rate models: Vasicek, CIR, Hull-White 1F, G2++.

Every simulator takes a ``numpy.random.Generator`` so results are reproducible
without touching global random state.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from ratesvol.curves import instantaneous_forward


# ----------------------------------------------------------------- Vasicek
def vasicek_simulate(r0, a, b, sigma, T, n_steps, n_paths, rng):
    """Exact Vasicek transition: dr = a(b - r)dt + sigma dW. Returns (n_paths, n_steps+1)."""
    dt = T / n_steps
    e = np.exp(-a * dt)
    sd = sigma * np.sqrt((1 - e**2) / (2 * a))
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = r0
    for i in range(n_steps):
        paths[:, i + 1] = b + (paths[:, i] - b) * e + sd * rng.standard_normal(n_paths)
    return paths


def vasicek_terminal_moments(r0, a, b, sigma, T):
    """Mean and std of r_T under Vasicek."""
    mean = b + (r0 - b) * np.exp(-a * T)
    std = sigma * np.sqrt((1 - np.exp(-2 * a * T)) / (2 * a))
    return mean, std


def vasicek_zcb(r, a, b, sigma, tau):
    """Zero-coupon bond P = A exp(-B r) with B = (1 - e^{-a tau})/a."""
    B = (1 - np.exp(-a * tau)) / a
    log_A = (b - sigma**2 / (2 * a**2)) * (B - tau) - sigma**2 * B**2 / (4 * a)
    return np.exp(log_A - B * r)


def vasicek_zero_rate(r, a, b, sigma, tau):
    """Continuously compounded zero rate implied by the Vasicek bond price."""
    return -np.log(vasicek_zcb(r, a, b, sigma, tau)) / tau


def calibrate_vasicek(T_grid, market_zero, x0=(0.03, 0.1, 0.05, 0.01)):
    """Least-squares fit of (r0, a, b, sigma) to a zero curve. Returns (params, rmse_bp)."""
    T_grid = np.asarray(T_grid, dtype=float)
    market_zero = np.asarray(market_zero, dtype=float)

    def sse(p):
        r0, a, b, s = p
        return np.sum((vasicek_zero_rate(r0, a, b, s, T_grid) - market_zero) ** 2)

    bounds = [(-0.05, 0.2), (0.01, 2.0), (-0.05, 0.3), (1e-4, 0.1)]
    res = minimize(sse, x0, method="L-BFGS-B", bounds=bounds)
    rmse_bp = np.sqrt(res.fun / len(T_grid)) * 1e4
    return res.x, rmse_bp


# --------------------------------------------------------------------- CIR
def feller_condition(a, b, sigma):
    """True when 2ab >= sigma^2 (zero is unattainable)."""
    return 2 * a * b >= sigma**2


def cir_simulate(r0, a, b, sigma, T, n_steps, n_paths, rng):
    """Full-truncation Euler for dr = a(b - r)dt + sigma sqrt(r) dW (Lord et al. 2010).

    The auxiliary process may dip below zero; the returned short rate is max(., 0).
    """
    dt = T / n_steps
    x = np.full(n_paths, float(r0))
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = r0
    for i in range(n_steps):
        xp = np.maximum(x, 0.0)
        x = x + a * (b - xp) * dt + sigma * np.sqrt(xp * dt) * rng.standard_normal(n_paths)
        paths[:, i + 1] = np.maximum(x, 0.0)
    return paths


# ------------------------------------------------------------ Hull-White 1F
def hw1f_theta(T_grid, market_zero, a, sigma):
    """theta(t) = df(0,t)/dt + a f(0,t) + sigma^2/(2a) (1 - e^{-2at}) on the curve grid."""
    T_grid = np.asarray(T_grid, dtype=float)
    f = instantaneous_forward(market_zero, T_grid)
    return np.gradient(f, T_grid) + a * f + sigma**2 / (2 * a) * (1 - np.exp(-2 * a * T_grid))


def hw1f_simulate(T_grid, market_zero, a, sigma, T, n_steps, n_paths, rng):
    """Euler simulation of dr = (theta(t) - a r)dt + sigma dW starting at r0 = f(0,0)."""
    T_grid = np.asarray(T_grid, dtype=float)
    theta = hw1f_theta(T_grid, market_zero, a, sigma)
    r0 = instantaneous_forward(market_zero, T_grid)[0]
    dt = T / n_steps
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = r0
    for i in range(n_steps):
        th = np.interp(i * dt, T_grid, theta)
        paths[:, i + 1] = (
            paths[:, i]
            + (th - a * paths[:, i]) * dt
            + sigma * np.sqrt(dt) * rng.standard_normal(n_paths)
        )
    return paths


def mc_zcb_from_short_rate(paths, T):
    """P(0,T) estimate = mean(exp(-integral r dt)) with the trapezoid rule. Returns (price, stderr)."""
    n_steps = paths.shape[1] - 1
    dt = T / n_steps
    integral = dt * (paths[:, 1:-1].sum(axis=1) + 0.5 * (paths[:, 0] + paths[:, -1]))
    disc = np.exp(-integral)
    return disc.mean(), disc.std(ddof=1) / np.sqrt(len(disc))


# -------------------------------------------------------------------- G2++
def g2pp_phi(t, T_grid, market_zero, a, b, sigma, eta, rho):
    """Deterministic shift that fits G2++ to the market curve (Brigo-Mercurio eq. 4.12)."""
    f = np.interp(t, T_grid, instantaneous_forward(market_zero, T_grid))
    ea, eb = 1 - np.exp(-a * t), 1 - np.exp(-b * t)
    return (
        f
        + sigma**2 / (2 * a**2) * ea**2
        + eta**2 / (2 * b**2) * eb**2
        + rho * sigma * eta / (a * b) * ea * eb
    )


def g2pp_simulate(T_grid, market_zero, a, b, sigma, eta, rho, T, n_steps, n_paths, rng):
    """Euler simulation of r = x + y + phi(t), dx = -a x dt + sigma dW1, dy = -b y dt + eta dW2.

    Returns (x, y, r), each (n_paths, n_steps+1).
    """
    dt = T / n_steps
    x = np.zeros((n_paths, n_steps + 1))
    y = np.zeros((n_paths, n_steps + 1))
    r = np.zeros((n_paths, n_steps + 1))
    r[:, 0] = g2pp_phi(0.0, T_grid, market_zero, a, b, sigma, eta, rho)
    for i in range(n_steps):
        z1 = rng.standard_normal(n_paths)
        z2 = rho * z1 + np.sqrt(1 - rho**2) * rng.standard_normal(n_paths)
        x[:, i + 1] = x[:, i] - a * x[:, i] * dt + sigma * np.sqrt(dt) * z1
        y[:, i + 1] = y[:, i] - b * y[:, i] * dt + eta * np.sqrt(dt) * z2
        phi = g2pp_phi((i + 1) * dt, T_grid, market_zero, a, b, sigma, eta, rho)
        r[:, i + 1] = x[:, i + 1] + y[:, i + 1] + phi
    return x, y, r
