"""Independent numerical references for the fixed-beta Hagan inverse problem.

Hagan et al. (2002), equations (2.17a-c) and (2.18), are transcribed in
dimensionless coordinates. This checks an approximate IV map, not exact SABR
prices, dynamics, arbitrage freedom or global parameter identifiability.
https://lesniewski.us/papers/published/ManagingSmileRisk.pdf

No production SABR/Black/optimizer helper is called. The beta=1, nu=0
lognormal price limit is checked separately by normal-density quadrature.
"""

from __future__ import annotations

import math
from time import perf_counter

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.special import ndtr

SCALE = np.array([0.20, 0.50, 0.50])
LOWER = np.array([0.05, -0.95, 0.0])
UPPER = np.array([0.50, 0.95, 1.5])
NOISE_SCALE = 0.0005


def _inputs(F, T, beta, theta, strikes):
    """Check the mathematical domain and return float arrays."""
    theta = np.asarray(theta, dtype=float)
    strikes = np.asarray(strikes, dtype=float)
    if (
        not np.isfinite([F, T, beta]).all()
        or F <= 0
        or T < 0
        or not 0 <= beta <= 1
        or theta.shape != (3,)
        or not np.isfinite(theta).all()
        or theta[0] <= 0
        or abs(theta[1]) >= 1
        or theta[2] < 0
        or strikes.ndim != 1
        or strikes.size == 0
        or not np.isfinite(strikes).all()
        or np.any(strikes <= 0)
    ):
        raise ValueError("positive F/strikes/a, nonnegative T/nu and valid beta/rho required")
    return theta, strikes


def _z_over_x(z, rho):
    """Evaluate z/x(z) with rationalized log1p and a cubic removable limit."""
    ratio = np.empty_like(z)
    small = np.abs(z) < 1e-4
    v = z[small]
    ratio[small] = (
        1 - rho * v / 2 + (2 - 3 * rho**2) * v**2 / 12 + rho * (5 - 6 * rho**2) * v**3 / 24
    )
    v = z[~small]
    root = np.hypot(v - rho, math.sqrt(1 - rho**2))
    root_minus_one = v * (v - 2 * rho) / (root + 1)
    positive = v >= 0
    x = np.empty_like(v)
    x[positive] = np.log1p((root_minus_one[positive] + v[positive]) / (1 - rho))
    x[~positive] = -np.log1p((root_minus_one[~positive] - v[~positive]) / (1 + rho))
    ratio[~small] = v / x
    return ratio


def independent_hagan_vols(F, T, beta, theta, strikes):
    """Return independently transcribed Hagan lognormal IVs, theta=(a,rho,nu).

    a=alpha/F**(1-beta). The ATM limit follows from log(F/K)=0 in the
    dimensionless formula. Small z retains quadratic/cubic terms that the
    public helper drops in its abs(z)<1e-6 first-order branch; tiny differences
    there are transcription/roundoff differences, not exact SABR model error.
    """
    theta, strikes = _inputs(F, T, beta, theta, strikes)
    a, rho, nu = theta
    b = 1 - beta
    log_fk = np.log(F / strikes)
    m = a * np.exp(b * log_fk / 2)  # alpha/(F*K)**((1-beta)/2)
    denominator = 1 + b**2 * log_fk**2 / 24 + b**4 * log_fk**4 / 1920
    z = nu * log_fk / m
    time_coefficient = b**2 * m**2 / 24 + rho * beta * nu * m / 4 + (2 - 3 * rho**2) * nu**2 / 24
    return m * _z_over_x(z, rho) * (1 + time_coefficient * T) / denominator


def black_calls(F, T, strikes, vols):
    """Return undiscounted Black calls using an independent vector formula."""
    strikes = np.asarray(strikes, dtype=float)
    vols = np.broadcast_to(np.asarray(vols, dtype=float), strikes.shape)
    if (
        not np.isfinite([F, T]).all()
        or F <= 0
        or T < 0
        or not np.isfinite(strikes).all()
        or np.any(strikes <= 0)
        or not np.isfinite(vols).all()
        or np.any(vols < 0)
    ):
        raise ValueError("positive F/strikes and nonnegative finite T/vols required")
    result = np.maximum(F - strikes, 0.0)
    total_vol = vols * math.sqrt(T)
    live = total_vol > 0
    d1 = np.log(F / strikes[live]) / total_vol[live] + total_vol[live] / 2
    d2 = d1 - total_vol[live]
    result[live] = F * ndtr(d1) - strikes[live] * ndtr(d2)
    return result


def flat_lognormal_quad(F, T, strike, alpha):
    """Integrate the beta=1, nu=0 lognormal payoff against a normal density.

    Completing the square in payoff*density avoids evaluating exp(alpha*z)
    at the infinite quadrature endpoint. The integral uses no normal CDF or
    Black price helper and is a separate method for this exact limit only.
    """
    if not np.isfinite([F, T, strike, alpha]).all() or F <= 0 or strike <= 0 or T < 0 or alpha < 0:
        raise ValueError("positive F/strike and nonnegative finite T/alpha required")
    s = alpha * math.sqrt(T)
    if s == 0:
        return float(max(F - strike, 0))
    threshold = (math.log(strike / F) + s * s / 2) / s
    denominator = math.sqrt(2 * math.pi)

    def payoff_density(z):
        return (F * math.exp(-0.5 * (z - s) ** 2) - strike * math.exp(-0.5 * z**2)) / denominator

    value, _ = quad(payoff_density, threshold, np.inf, epsabs=1e-12, epsrel=1e-12, limit=200)
    return float(value)


def independent_jacobian(F, T, beta, theta, strikes, noise_scale=0.0005, h=1e-4):
    """Return d(IV/noise_scale)/du for u=(a/.20,rho/.50,nu/.50).

    Interior columns use an independent five-point stencil. Exactly nu=0
    uses the analytic right derivative in nu and analytic a/rho derivatives:
    rho disappears from IV, but dIV/dnu is generally nonzero when rho!=0.
    At rho=nu=0 only the a column remains. This preserves structural zeros
    without inheriting cancellation in production's logarithm.
    """
    theta, strikes = _inputs(F, T, beta, theta, strikes)
    if not np.isfinite([noise_scale, h]).all() or noise_scale <= 0 or h <= 0:
        raise ValueError("positive finite noise_scale and h required")
    a, rho, nu = theta
    if nu == 0:
        b = 1 - beta
        log_fk = np.log(F / strikes)
        m = a * np.exp(b * log_fk / 2)
        denom = 1 + b**2 * log_fk**2 / 24 + b**4 * log_fk**4 / 1920
        c0 = b**2 * m**2 / 24
        da = (m / a) * (1 + 3 * c0 * T) / denom
        dnu = rho * (-log_fk * (1 + c0 * T) / 2 + beta * m**2 * T / 4) / denom
        return np.column_stack([da, np.zeros_like(da), dnu]) * SCALE / noise_scale

    columns = []
    for axis in range(3):
        distance = theta[axis] if axis in (0, 2) else 1 - abs(theta[axis])
        step = min(h, distance / (4 * SCALE[axis]))
        bump = np.zeros(3)
        bump[axis] = step * SCALE[axis]
        pp = independent_hagan_vols(F, T, beta, theta + 2 * bump, strikes)
        p = independent_hagan_vols(F, T, beta, theta + bump, strikes)
        m = independent_hagan_vols(F, T, beta, theta - bump, strikes)
        mm = independent_hagan_vols(F, T, beta, theta - 2 * bump, strikes)
        columns.append((-pp + 8 * p - 8 * m + mm) / (12 * step * noise_scale))
    return np.column_stack(columns)


class _EvaluationBudgetError(Exception):
    """Internal stop when actual objective calls consume their fixed budget."""


def independent_fixed_fit(F, T, beta, strikes, quotes, start, fixed=None, max_nfev=250):
    """Fit the independent Hagan map with bounded scaled-coordinate SLSQP.

    fixed={axis:value}, axes=(a,rho,nu). Bounds are a[.05,.50],
    rho[-.95,.95], nu[0,1.5]. Stored Q=sum((IV-quotes)/.0005)**2;
    SLSQP minimizes Q/10000 to temper gradient magnitudes without changing
    minimizers. max_nfev caps actual objective calls, not price evaluations
    inside the independent five-point Jacobian. A budget failure is retained.
    Solver success is local numerical convergence, not global identification.
    """
    started = perf_counter()
    theta, strikes = _inputs(F, T, beta, start, strikes)
    theta = theta.copy()
    quotes = np.asarray(quotes, dtype=float)
    if quotes.shape != strikes.shape or not np.isfinite(quotes).all() or np.any(quotes <= 0):
        raise ValueError("finite positive quotes must match strikes")
    if not isinstance(max_nfev, int) or max_nfev < 1:
        raise ValueError("positive integer objective evaluation budget required")
    fixed = {} if fixed is None else dict(fixed)
    for axis, value in fixed.items():
        if axis not in (0, 1, 2) or not np.isfinite(value):
            raise ValueError("fixed axes are 0=a, 1=rho, 2=nu")
        theta[axis] = value
    if np.any(theta < LOWER) or np.any(theta > UPPER):
        raise ValueError("start/fixed parameters lie outside the research bounds")
    free = [axis for axis in range(3) if axis not in fixed]
    state = {"nfev": 0, "best_q": math.inf, "best_theta": theta.copy()}
    objective_factor = 10000.0

    def unpack(u):
        point = theta.copy()
        point[free] = np.asarray(u) * SCALE[free]
        return point

    def objective(u):
        if state["nfev"] >= max_nfev:
            raise _EvaluationBudgetError
        state["nfev"] += 1
        point = unpack(u)
        residual = (independent_hagan_vols(F, T, beta, point, strikes) - quotes) / NOISE_SCALE
        q = float(residual @ residual)
        if q < state["best_q"]:
            state.update(best_q=q, best_theta=point.copy())
        return q / objective_factor

    def gradient(u):
        point = unpack(u)
        residual = (independent_hagan_vols(F, T, beta, point, strikes) - quotes) / NOISE_SCALE
        jac = independent_jacobian(F, T, beta, point, strikes)
        return 2 * jac[:, free].T @ residual / objective_factor

    if not free:
        objective([])
        point, success, status, message = theta, True, 0, "All axes fixed; objective evaluated."
    else:
        try:
            result = minimize(
                objective,
                theta[free] / SCALE[free],
                jac=gradient,
                method="SLSQP",
                bounds=list(zip(LOWER[free] / SCALE[free], UPPER[free] / SCALE[free], strict=True)),
                options={"ftol": 1e-15, "maxiter": max_nfev, "disp": False},
            )
            point = unpack(result.x)
            success, status, message = bool(result.success), int(result.status), str(result.message)
        except _EvaluationBudgetError:
            point = state["best_theta"]
            success, status, message = False, 9, "Actual objective evaluation budget exhausted."
    residual = (independent_hagan_vols(F, T, beta, point, strikes) - quotes) / NOISE_SCALE
    return {
        "theta": np.asarray(point),
        "q": float(residual @ residual),
        "success": success,
        "status": status,
        "message": message,
        "nfev": state["nfev"],
        "seconds": perf_counter() - started,
        "method": "SLSQP",
        "objective_scale": objective_factor,
    }
