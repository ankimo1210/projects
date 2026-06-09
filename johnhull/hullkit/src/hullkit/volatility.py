"""Implied volatility and volatility estimation (Hull 11e, Ch.20 / Ch.23)."""

import numpy as np
from scipy.optimize import brentq, minimize

from . import bsm


def implied_vol(price, S, K, r, T, q=0.0, kind="call"):
    """Implied BSM volatility via Brent's method on [1e-6, 5] (Hull Ch.20)."""
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    price_f = bsm.call_price if kind == "call" else bsm.put_price

    def objective(sigma):
        return price_f(S, K, r, sigma, T, q) - price

    lo, hi = 1e-6, 5.0
    if objective(lo) * objective(hi) > 0:
        raise ValueError("price outside no-arbitrage bounds for sigma in [1e-6, 5]")
    return brentq(objective, lo, hi)


def ewma_variance(returns, lam=0.94, init=None):
    """EWMA variance series (Hull eq. 23.7); var[0] = init or returns[0]**2."""
    u = np.asarray(returns, dtype=float)
    if u.size == 0:
        raise ValueError("returns must be non-empty")
    var = np.empty_like(u)
    var[0] = init if init is not None else u[0] ** 2
    for i in range(1, len(u)):
        var[i] = lam * var[i - 1] + (1.0 - lam) * u[i - 1] ** 2
    return var


def garch11_variance(returns, omega, alpha, beta, init=None):
    """GARCH(1,1) conditional variance series (Hull eq. 23.9)."""
    u = np.asarray(returns, dtype=float)
    if u.size == 0:
        raise ValueError("returns must be non-empty")
    var = np.empty_like(u)
    var[0] = init if init is not None else float(np.var(u))
    for i in range(1, len(u)):
        var[i] = omega + alpha * u[i - 1] ** 2 + beta * var[i - 1]
    return var


def garch11_long_run(omega, alpha, beta):
    """Long-run variance V_L = omega / (1 - alpha - beta)."""
    if alpha + beta >= 1.0:
        raise ValueError("alpha + beta must be < 1 for stationarity")
    return omega / (1.0 - alpha - beta)


def garch11_forecast(sigma2_n, k, omega, alpha, beta):
    """k-step-ahead expected variance E[sigma^2_{n+k}] (Hull eq. 23.13)."""
    v_l = garch11_long_run(omega, alpha, beta)
    return v_l + (alpha + beta) ** k * (sigma2_n - v_l)


def garch11_fit(returns, x0=(2e-6, 0.10, 0.85)):
    """Fit GARCH(1,1) by MLE (Hull eq. 23.12). Returns (omega, alpha, beta).

    Nelder-Mead with stationarity/positivity penalties — gradient-free is
    robust for this likelihood surface.
    """
    u = np.asarray(returns, dtype=float)

    def neg_loglik(params):
        omega, alpha, beta = params
        if omega <= 0.0 or alpha < 0.0 or beta < 0.0 or alpha + beta >= 0.999:
            return 1e10
        var = np.maximum(garch11_variance(u, omega, alpha, beta), 1e-12)
        return float(np.sum(np.log(var) + u**2 / var))

    res = minimize(
        neg_loglik,
        x0,
        method="Nelder-Mead",
        options={"xatol": 1e-10, "fatol": 1e-8, "maxiter": 5000},
    )
    if not res.success:
        raise ValueError(f"garch11_fit did not converge: {res.message}")
    return tuple(float(x) for x in res.x)
