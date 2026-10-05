"""Private Hull §31.2 equilibrium Vasicek/CIR/Rendleman–Bartter models.

Instantaneous rates are continuous annual decimals. Vasicek sigma is an
absolute rate/sqrt(year); CIR sigma multiplies sqrt(rate); RB sigma is
relative/sqrt(year). CIR exact endpoint sampling does not exactly sample
its integrated short rate. RB discounting likewise needs time refinement.
"""

import math

import numpy as np


def _parameters(rate, a, b, sigma, horizon, *, cir=False):
    if min(a, sigma, horizon) < 0:
        raise ValueError("nonnegative mean reversion, volatility and time required")
    if cir and (b < 0 or np.any(np.asarray(rate) < 0)):
        raise ValueError("CIR requires nonnegative level and rate")


def mean_reversion_loading(a, horizon):
    """B=(1-exp(-a*T))/a, with the a=0 limit T."""
    if min(a, horizon) < 0:
        raise ValueError("nonnegative mean reversion and time required")
    return horizon if a == 0 else -math.expm1(-a * horizon) / a


def vasicek_bond(rate, a, b, sigma, horizon):
    """P=A exp(-B*r), plus conditional rate/integral Gaussian moments."""
    _parameters(rate, a, b, sigma, horizon)
    T = horizon
    B = mean_reversion_loading(a, T)
    B2 = mean_reversion_loading(2 * a, T)
    x = a * T
    if x < 0.01:
        # Integrate the squared kernel series, avoiding cancellation near a=0.
        coefficients = np.array([0.0] + [(-x) ** (n - 1) / math.factorial(n) for n in range(1, 11)])
        square = np.polynomial.polynomial.polymul(coefficients, coefficients)
        variance = sigma * sigma * T**3 * float(np.sum(square / np.arange(1, len(square) + 1)))
    else:
        variance = sigma * sigma * (T - 2 * B + B2) / (a * a)
    logA = -b * (T - B) + 0.5 * variance
    r = np.asarray(rate, dtype=float)
    return {
        "B": B,
        "logA": logA,
        "price": np.exp(logA - B * r),
        "mean_rate": b + (r - b) * math.exp(-a * T),
        "variance_rate": sigma * sigma * B2,
        "mean_integral": r * B + b * (T - B),
        "variance_integral": variance,
        "cov_rate_integral": 0.5 * sigma * sigma * B * B,
    }


def cir_bond(rate, a, b, sigma, horizon):
    """Canonical Hull A/B, scaled with exp(-gamma*T) to avoid overflow."""
    _parameters(rate, a, b, sigma, horizon, cir=True)
    if sigma == 0:
        B = mean_reversion_loading(a, horizon)
        logA = -b * (horizon - B)
    elif horizon == 0:
        B, logA = 0.0, 0.0
    else:
        gamma = math.sqrt(a * a + 2 * sigma * sigma)
        decay = math.exp(-gamma * horizon)
        one_minus = -math.expm1(-gamma * horizon)
        denominator = (gamma + a) * one_minus + 2 * gamma * decay
        B = 2 * one_minus / denominator
        logA = (2 * a * b / sigma**2) * (
            math.log(2 * gamma) + (a - gamma) * horizon / 2 - math.log(denominator)
        )
    return {"B": B, "logA": logA, "price": np.exp(logA - B * np.asarray(rate, dtype=float))}


def cir_transition_law(rate, a, b, sigma, delta):
    """Scaled noncentral chi-square endpoint law, including zero immigration.

    With a*b>0 the positive-time endpoint has no zero atom, even below the
    Feller boundary. With a*b=0 it has an absorbing-zero atom. Degenerate
    sigma=0/time=0 gives a deterministic endpoint, not a chi-square sample.
    """
    _parameters(rate, a, b, sigma, delta, cir=True)
    r = np.asarray(rate, dtype=float)
    decay = math.exp(-a * delta)
    B = mean_reversion_loading(a, delta)
    mean = r * decay + b * (-math.expm1(-a * delta))
    variance = sigma * sigma * (r * decay * B + a * b * B * B / 2)
    scale = sigma * sigma * B / 4
    degrees = 4 * a * b / sigma**2 if sigma else 0.0
    nc = r * decay / scale if scale else np.zeros_like(r)
    atom = np.exp(-nc / 2) if degrees == 0 and scale else np.zeros_like(r)
    if not scale:
        atom = np.asarray(mean == 0, dtype=float)
    return {
        "mean": mean,
        "variance": variance,
        "scale": scale,
        "degrees": degrees,
        "noncentrality": nc,
        "zero_atom": atom,
        "feller": 2 * a * b >= sigma * sigma,
    }


def cir_transition(rate, a, b, sigma, delta, rng, *, size=None):
    """Exact nonnegative endpoint; df=0 uses a Poisson/gamma mixture."""
    law = cir_transition_law(rate, a, b, sigma, delta)
    if law["scale"] == 0:
        return np.broadcast_to(law["mean"], size).copy() if size is not None else law["mean"]
    if law["degrees"] > 0:
        return law["scale"] * rng.noncentral_chisquare(
            law["degrees"], law["noncentrality"], size=size
        )
    counts = np.asarray(rng.poisson(law["noncentrality"] / 2, size=size))
    positive = counts > 0
    chi = np.zeros(counts.shape, dtype=float)
    chi[positive] = rng.gamma(counts[positive], 2.0)
    return law["scale"] * chi


def cir_transition_laplace(argument, rate, a, b, sigma, delta):
    """Conditional E[exp(-argument*r_next)], including the df=0 atom."""
    if argument < 0:
        raise ValueError("nonnegative Laplace argument required")
    law = cir_transition_law(rate, a, b, sigma, delta)
    if law["scale"] == 0:
        return np.exp(-argument * law["mean"])
    denominator = 1 + 2 * law["scale"] * argument
    return denominator ** (-law["degrees"] / 2) * np.exp(
        -law["noncentrality"] * law["scale"] * argument / denominator
    )


def matching_cir_volatility(vasicek_volatility, rate):
    """CIR sigma giving the Vasicek instantaneous rate volatility at rate r."""
    if vasicek_volatility < 0 or rate <= 0:
        raise ValueError("nonnegative vol and positive rate required")
    return vasicek_volatility / math.sqrt(rate)


def short_rate_bond_risk(which, rate, a, b, sigma, times, cashflows):
    """PV-weighted B/B²: instantaneous short-rate duration/convexity.

    These differ from market yield duration. Relative diffusion is signed,
    negative for a positive-cashflow bond with either nonnegative diffusion.
    """
    if which not in ("vasicek", "cir"):
        raise ValueError("model must be vasicek or cir")
    function = vasicek_bond if which == "vasicek" else cir_bond
    t, c = np.asarray(times, dtype=float), np.asarray(cashflows, dtype=float)
    if t.ndim != 1 or not t.size or t.shape != c.shape:
        raise ValueError("matching cashflow vectors required")
    rows = [function(rate, a, b, sigma, float(ti)) for ti in t]
    pv = c * np.array([row["price"] for row in rows])
    price = float(pv.sum())
    if price == 0:
        raise ValueError("risk ratios require nonzero price")
    load = np.array([row["B"] for row in rows])
    duration = float(pv @ load / price)
    diffusion = sigma if which == "vasicek" else sigma * math.sqrt(rate)
    return {
        "price": price,
        "duration": duration,
        "convexity": float(pv @ (load * load) / price),
        "relative_diffusion": -diffusion * duration,
    }


def rb_paths(initial_rate, drift, volatility, time_grid, brownian_increments):
    """Exact GBM endpoints for RB; supplied Brownian increments fix sampling."""
    t = np.asarray(time_grid, dtype=float)
    dw = np.asarray(brownian_increments, dtype=float)
    if initial_rate < 0 or volatility < 0 or t.ndim != 1 or t.size < 2 or np.any(np.diff(t) <= 0):
        raise ValueError("nonnegative rate/vol and increasing time grid required")
    if dw.ndim == 0 or dw.shape[-1] != t.size - 1:
        raise ValueError("increments must match time steps")
    W = np.concatenate([np.zeros((*dw.shape[:-1], 1)), np.cumsum(dw, axis=-1)], axis=-1)
    return initial_rate * np.exp(
        (drift - 0.5 * volatility * volatility) * (t - t[0]) + volatility * W
    )


def rb_deterministic_bond(initial_rate, drift, horizon):
    """Zero-volatility RB discount; general RB has no claimed closed form."""
    if min(initial_rate, horizon) < 0:
        raise ValueError("nonnegative initial rate/time required")
    integral = initial_rate * (horizon if drift == 0 else math.expm1(drift * horizon) / drift)
    return math.exp(-integral)
