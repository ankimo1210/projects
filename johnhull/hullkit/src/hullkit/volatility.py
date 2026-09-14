"""Implied volatility and volatility estimation (Hull 11e, Ch.20 / Ch.23)."""

import numpy as np
from scipy.optimize import brentq, minimize
from scipy.stats import norm

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


def breeden_litzenberger_density(strikes, call_prices, r, T):
    """Risk-neutral density of S_T from call prices, Hull 11e GE Appendix 20A p.468.

    Butterfly finite difference of eq. (20A.2) on an equally spaced strike grid
    ``K_0 < K_1 < ... < K_m`` with spacing ``delta``::

        g(K_i) = e^{rT} (c(K_i - delta) + c(K_i + delta) - 2 c(K_i)) / delta^2

    for the interior strikes ``K_1..K_{m-1}`` (eq. 20A.1 is the limit
    ``g = e^{rT} d^2c/dK^2``). Returns ``(interior_strikes, density)``. For
    Example 20A.1 pass the grid 6.0, 6.5, ..., 14.0 and read g1..g8 at
    6.5, 7.5, ..., 13.5. No smoothing or positivity repair is applied: a
    negative value flags butterfly arbitrage in the input prices.
    """
    k = np.asarray(strikes, dtype=float)
    c = np.asarray(call_prices, dtype=float)
    if k.ndim != 1 or c.ndim != 1 or k.shape != c.shape:
        raise ValueError("strikes and call_prices must be 1-D arrays of equal length")
    if k.size < 3:
        raise ValueError("at least 3 strikes are needed for the butterfly difference")
    if np.any(~np.isfinite(k)) or np.any(~np.isfinite(c)):
        raise ValueError("strikes and call_prices must be finite")
    spacing = np.diff(k)
    delta = (k[-1] - k[0]) / (k.size - 1)
    if np.any(spacing <= 0.0) or not np.allclose(spacing, delta, rtol=1e-6, atol=0.0):
        raise ValueError("strikes must be strictly increasing and equally spaced (eq. 20A.2)")
    if np.ndim(r) != 0 or not np.isfinite(r):
        raise ValueError("r must be a finite scalar")
    if np.ndim(T) != 0 or not np.isfinite(T) or T < 0.0:
        raise ValueError("T must be a finite scalar >= 0")
    density = np.exp(r * T) * (c[:-2] + c[2:] - 2.0 * c[1:-1]) / delta**2
    return k[1:-1], density


def forward_moneyness(K, S0, r, T, q=0.0):
    """Moneyness ``K / F0`` with ``F0 = S0 e^{(r-q)T}``, Hull 11e GE §20.4 p.458.

    The smile axis traders prefer to ``K/S0`` because ``F0`` (eq. 5.3), not
    ``S0``, is the risk-neutral expected price at the options' maturity;
    ``K = F0`` is the at-the-money strike on this axis.
    """
    bsm._validate_price_inputs(S0, K, 0.0, T)
    return K / (S0 * np.exp((r - q) * T))


def strike_from_forward_moneyness(moneyness, S0, r, T, q=0.0):
    """Inverse of `forward_moneyness`: ``K = (K/F0) S0 e^{(r-q)T}``, Hull 11e GE §20.4 p.458."""
    m = np.asarray(moneyness, dtype=float)
    if np.any(~np.isfinite(m)) or np.any(m <= 0.0):
        raise ValueError("moneyness must contain only finite values > 0")
    bsm._validate_price_inputs(S0, 1.0, 0.0, T)
    return moneyness * S0 * np.exp((r - q) * T)


def delta_from_strike(K, S0, r, sigma, T, q=0.0, kind="call"):
    """Delta axis of a smile, Hull 11e GE §20.4 p.458 with Table 19.6 deltas.

    Each strike's own implied vol ``sigma`` (array-aligned with ``K``) gives
    the option's BSM delta: ``e^{-qT} N(d1)`` for calls, ``e^{-qT}(N(d1) - 1)``
    for puts. Plotting ``sigma`` against the result re-expresses a
    ``sigma(K)`` smile on the delta axis (0.5 call delta = "50-delta").
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    delta_fn = bsm.call_delta if kind == "call" else bsm.put_delta
    return delta_fn(S0, K, r, sigma, T, q)


def strike_from_delta(delta, S0, r, sigma, T, q=0.0, kind="call"):
    """Strike whose BSM delta at vol ``sigma`` equals ``delta``, Hull 11e GE §20.4 p.458.

    Inverts Table 19.6: ``N(d1) = delta e^{qT}`` (call) or ``1 + delta e^{qT}``
    (put), then ``K = S0 exp(-d1 sigma sqrt(T) + (r - q + sigma^2/2) T)``.
    Maps a smile quoted on the delta axis back to strikes. Requires
    ``0 < delta < e^{-qT}`` for calls and ``-e^{-qT} < delta < 0`` for puts.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    bsm._validate_price_inputs(S0, 1.0, sigma, T)
    if np.any(np.asarray(sigma) == 0.0) or np.any(np.asarray(T) == 0.0):
        raise ValueError("strike_from_delta needs sigma > 0 and T > 0")
    delta = np.asarray(delta, dtype=float)
    growth = np.exp(q * T)
    n_d1 = delta * growth if kind == "call" else 1.0 + delta * growth
    if np.any(~np.isfinite(n_d1)) or np.any(n_d1 <= 0.0) or np.any(n_d1 >= 1.0):
        bound = "0 < delta < e^{-qT}" if kind == "call" else "-e^{-qT} < delta < 0"
        raise ValueError(f"{kind} delta must satisfy {bound}")
    vol_time = sigma * np.sqrt(T)
    return S0 * np.exp(-norm.ppf(n_d1) * vol_time + (r - q + 0.5 * sigma**2) * T)


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


def ewma_covariance(x, y, lam=0.94, init=None):
    """EWMA covariance series of two aligned return series (Hull §23.7).

    cov[i] = lam*cov[i-1] + (1-lam)*x[i-1]*y[i-1]; cov[0]=init or x[0]*y[0].
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size != y.size:
        raise ValueError("x and y must have equal length")
    if x.size == 0:
        raise ValueError("inputs must be non-empty")
    cov = np.empty_like(x)
    cov[0] = init if init is not None else x[0] * y[0]
    for i in range(1, x.size):
        cov[i] = lam * cov[i - 1] + (1.0 - lam) * x[i - 1] * y[i - 1]
    return cov


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
