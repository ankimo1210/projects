"""Private Hull §31.1: path discount, zero yield and short-rate pricing PDE."""

import numpy as np


def discounted_path_values(short_rates, time_grid, payoffs=1.0):
    """exp(-integral r dt)*terminal payoff; trapezoidal path integration.

    Rate paths end on the final axis; times are explicit years and rates
    are continuously compounded. The result remains a per-path value, so
    callers can report Monte Carlo standard errors rather than just a mean.
    """
    r = np.asarray(short_rates, dtype=float)
    t = np.asarray(time_grid, dtype=float)
    if t.ndim != 1 or t.size < 2 or np.any(np.diff(t) <= 0) or np.any(t < 0):
        raise ValueError("increasing nonnegative time grid required")
    if r.ndim == 0 or r.shape[-1] != t.size:
        raise ValueError("rate paths must match the final time axis")
    integral = np.sum((r[..., :-1] + r[..., 1:]) * 0.5 * np.diff(t), axis=-1)
    return np.exp(-integral) * payoffs


def zero_yield(discount, horizon):
    """Continuous zero yield -log(P)/(T-t); undefined at zero horizon."""
    p = np.asarray(discount, dtype=float)
    if horizon <= 0 or np.any(p <= 0):
        raise ValueError("positive horizon and discount required")
    return -np.log(p) / horizon


def gaussian_drift_bond(rate, drift, volatility, horizon):
    """Exact ZCB for dr=m dt+sigma dW, constant Q coefficients."""
    if horizon < 0 or volatility < 0:
        raise ValueError("nonnegative time and volatility required")
    return np.exp(
        -np.asarray(rate) * horizon - 0.5 * drift * horizon**2 + volatility**2 * horizon**3 / 6
    )


def short_rate_pde_residual(v_t, v_r, v_rr, value, rate, drift, diffusion):
    """V_t + m V_r + s^2 V_rr/2 - r V for a no-income Markov claim."""
    if np.any(np.asarray(diffusion) < 0):
        raise ValueError("nonnegative diffusion required")
    return v_t + drift * v_r + 0.5 * diffusion**2 * v_rr - rate * value


def flat_curve_pde_residual(rate, horizon, drift, diffusion):
    """Residual of P=exp(-r*(T-t)); zero for every maturity only if m=s=0.

    An initially flat calibrated curve is distinct from requiring every
    future curve to remain flat with a stochastically changing short rate.
    """
    tau = np.asarray(horizon, dtype=float)
    if np.any(tau < 0) or diffusion < 0:
        raise ValueError("nonnegative horizons/diffusion required")
    return np.exp(-rate * tau) * (-drift * tau + 0.5 * diffusion**2 * tau**2)
