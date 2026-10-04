"""Private Hull §31.4 P time-series estimation then Q risk-price calibration.

The original 3-month-rate proxy uses one 1/250-year step per observed pair;
calendar gaps are not silently substituted. Fit rates are decimals. Euler
OLS, Euler ML and exact OU ML have different variance conventions. Curve
calibration holds physical parameters fixed, fitting only the risk price.
"""

import math

import numpy as np
from scipy.optimize import minimize_scalar

from ._short_rate_models import cir_bond, vasicek_bond


def _series(rates, delta):
    r = np.asarray(rates, dtype=float)
    if r.ndim != 1 or r.size < 4 or not np.all(np.isfinite(r)) or delta <= 0:
        raise ValueError("at least four finite rates and positive observed step required")
    return r[:-1], np.diff(r)


def fit_vasicek_series(rates, delta, method="euler_ols"):
    """OLS of delta-r on previous r, or the corresponding Gaussian ML fit.

    Exact OU uses the unrestricted AR(1) optimum only when its coefficient
    is positive, as required by a continuous OU transition. a=0 reports
    drift directly and b=None, avoiding a fictitious finite long-run mean.
    """
    if method not in ("euler_ols", "euler_mle", "exact_ou_mle"):
        raise ValueError("unknown estimation method")
    x, y = _series(rates, delta)
    n = x.size
    design = np.column_stack([np.ones(n), x])
    if np.linalg.matrix_rank(design) < 2:
        raise ValueError("rate variation required for regression")
    intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - intercept - slope * x
    df = n - 2 if method == "euler_ols" else n
    innovation = float(residual @ residual / df)
    if innovation <= 0:
        raise ValueError("positive residual variance required for Gaussian likelihood")
    a = -slope / delta
    c = intercept / delta
    if method == "exact_ou_mle":
        rho = 1 + slope
        if rho <= 0:
            raise ValueError("exact OU transition requires positive AR coefficient")
        a = -math.log1p(slope) / delta
        b = -intercept / slope if slope else None
        c = a * b if b is not None else intercept / delta
        ratio = 1 / delta if a == 0 else 2 * a / (-math.expm1(-2 * a * delta))
        sigma = math.sqrt(innovation * ratio)
    else:
        b = c / a if a != 0 else None
        sigma = math.sqrt(innovation / delta)
    loglik = -0.5 * (
        n * math.log(2 * math.pi * innovation) + float(residual @ residual) / innovation
    )
    return {
        "method": method,
        "pairs": n,
        "delta": delta,
        "intercept": float(intercept),
        "slope": float(slope),
        "residual_sd": math.sqrt(innovation),
        "a": float(a),
        "constant_drift": float(c),
        "b": None if b is None else float(b),
        "sigma": sigma,
        "log_likelihood": loglik,
    }


def fit_cir_euler_series(rates, delta):
    """Euler Gaussian pseudo-ML (conditional variance sigma²*r_previous*dt).

    This is not the exact noncentral-chi-square likelihood. Its weighted
    regression requires positive previous rates, since variance at zero
    vanishes. The result does not enforce stationarity/Feller by projection.
    """
    x, y = _series(rates, delta)
    if np.any(x <= 0):
        raise ValueError("Euler CIR likelihood needs positive previous rates")
    design = np.column_stack([np.ones(x.size), x])
    rootweight = 1 / np.sqrt(x)
    if np.linalg.matrix_rank(design) < 2:
        raise ValueError("rate variation required")
    alpha, beta = np.linalg.lstsq(rootweight[:, None] * design, rootweight * y, rcond=None)[0]
    residual = y - alpha - beta * x
    variance = float(np.mean(residual * residual / x))
    if variance <= 0:
        raise ValueError("positive weighted innovation variance required")
    a = -beta / delta
    c = alpha / delta
    sigma = math.sqrt(variance / delta)
    loglik = -0.5 * float(
        np.sum(np.log(2 * math.pi * variance * x) + residual * residual / (variance * x))
    )
    return {
        "pairs": x.size,
        "a": float(a),
        "constant_drift": float(c),
        "b": float(c / a) if a else None,
        "sigma": sigma,
        "log_likelihood": loglik,
    }


def _curve(times, market_zeros, weights):
    t, z = np.asarray(times, dtype=float), np.asarray(market_zeros, dtype=float)
    w = np.ones_like(t) if weights is None else np.asarray(weights, dtype=float)
    if t.ndim != 1 or not t.size or t.shape != z.shape or t.shape != w.shape:
        raise ValueError("matching nonempty curve vectors required")
    if np.any(t <= 0) or np.any(w < 0) or not np.any(w > 0):
        raise ValueError("positive tenors and nonnegative nonzero weights required")
    return t, z, w


def _zeros(function, rate, a, b, sigma, times):
    rows = [function(rate, a, b, sigma, float(t)) for t in times]
    return np.array(
        [(-row["logA"] + row["B"] * rate) / t for row, t in zip(rows, times, strict=True)]
    )


def fit_vasicek_risk_price(rate, a, b_p, sigma, times, market_zeros, weights=None):
    """Weighted continuous-zero SSE; model zeros are affine in lambda.

    b_Q=b_P-lambda*sigma/a, using b_P=0.0168 in the rounded book example;
    the printed 0.168 is inconsistent with the preceding P estimate.
    """
    if a <= 0 or sigma <= 0:
        raise ValueError("positive a/sigma required to identify risk price")
    t, market, w = _curve(times, market_zeros, weights)
    base = _zeros(vasicek_bond, rate, a, b_p, sigma, t)
    loading = _zeros(vasicek_bond, rate, a, b_p - sigma / a, sigma, t) - base
    denominator = float(np.sum(w * loading * loading))
    if denominator == 0:
        raise ValueError("nonzero risk-price loading required")
    risk = float(np.sum(w * loading * (market - base)) / denominator)
    fitted = base + risk * loading
    residual = fitted - market
    return {
        "risk_price": risk,
        "a_q": a,
        "b_q": b_p - risk * sigma / a,
        "model_zeros": fitted,
        "residuals": residual,
        "sse": float(np.sum(w * residual * residual)),
    }


def fit_cir_risk_price(rate, a_p, b_p, sigma, times, market_zeros, weights=None):
    """Canonical CIR curve fit with invariant a*b and a_Q=a_P+k*sigma.

    Auxiliary original Problem31_16.xls's saved B denominator differs from
    Hull's CIR expression. This uses canonical mathematics; its optimum is
    not represented as reproduction of that worksheet's saved Solver fit.
    """
    if sigma <= 0 or a_p * b_p < 0:
        raise ValueError("positive sigma and nonnegative immigration required")
    t, market, w = _curve(times, market_zeros, weights)
    c = a_p * b_p

    def objective(loga):
        a = math.exp(loga)
        residual = _zeros(cir_bond, rate, a, c / a, sigma, t) - market
        return float(np.sum(w * residual * residual))

    fit = minimize_scalar(objective, bounds=(-12, 3), method="bounded", options={"xatol": 1e-11})
    if not fit.success:
        raise ValueError("CIR risk-price fit failed")
    a = math.exp(fit.x)
    b = c / a
    fitted = _zeros(cir_bond, rate, a, b, sigma, t)
    residual = fitted - market
    return {
        "risk_price": (a - a_p) / sigma,
        "a_q": a,
        "b_q": b,
        "model_zeros": fitted,
        "residuals": residual,
        "sse": float(np.sum(w * residual * residual)),
    }
