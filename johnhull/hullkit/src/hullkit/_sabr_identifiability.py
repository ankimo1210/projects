"""Private fixed-beta Hagan inverse-problem diagnostics; no RNG or public API.

``theta=(a,rho,nu)``, ``alpha=a*F**(1-beta)``, and ``u=theta/SCALE``.
Raw IV Jacobians use physical ``(alpha,rho,nu)``; theta Jacobians use
``(a,rho,nu)``; scaled Jacobians differentiate ``IV/noise_scale`` in ``u``.
The finite-difference SVD is a local diagnostic of the Hagan approximation,
not a claim about global identifiability or exact SABR dynamics.
"""

from __future__ import annotations

from time import perf_counter

import numpy as np
from scipy.optimize import least_squares

from . import sabr

SCALE = np.array([0.20, 0.50, 0.50])
LOWER = np.array([0.05, -0.95, 0.0])
UPPER = np.array([0.50, 0.95, 1.5])


def _inputs(F, T, beta, theta, strikes):
    if not np.isfinite([F, T, beta]).all() or F <= 0 or T <= 0 or not 0 <= beta <= 1:
        raise ValueError("finite F,T>0 and beta in [0,1] required")
    theta = np.asarray(theta, dtype=float)
    strikes = np.asarray(strikes, dtype=float)
    if theta.shape != (3,) or not np.isfinite(theta).all():
        raise ValueError("theta must contain three finite values")
    if theta[0] <= 0 or abs(theta[1]) >= 1 or theta[2] < 0:
        raise ValueError("a>0, abs(rho)<1, nu>=0 required")
    if (
        strikes.ndim != 1
        or not strikes.size
        or not np.isfinite(strikes).all()
        or np.any(strikes <= 0)
    ):
        raise ValueError("nonempty finite positive strikes required")
    return theta, strikes


def _bounded(theta):
    if np.any(theta < LOWER) or np.any(theta > UPPER):
        raise ValueError("theta outside research bounds")


def _noise_scale(noise_scale):
    if not np.isfinite(noise_scale) or noise_scale <= 0:
        raise ValueError("positive finite noise_scale required")


def sabr_vols(F, T, beta, theta, strikes):
    """Return Hagan lognormal IVs with alpha=a*F**(1-beta), including nu=0.

    The research fitting box is not imposed on this pure forward mapping;
    mathematically valid positive a, abs(rho)<1, nu>=0 are required.
    """
    theta, strikes = _inputs(F, T, beta, theta, strikes)
    a, rho, nu = theta
    alpha = a * F ** (1 - beta)
    iv = np.array([sabr.sabr_implied_vol(F, k, T, alpha, beta, rho, nu) for k in strikes])
    if not np.isfinite(iv).all() or np.any(iv <= 0):
        raise ValueError("Hagan approximation produced invalid implied volatility")
    return iv


def _zero_nu_columns(F, T, beta, theta, strikes, noise_scale):
    """Analytic rho/nu derivatives at exactly nu=0; no teacher evaluations."""
    if theta[2] != 0:
        return {}
    a, rho, _ = theta
    alpha = a * F ** (1 - beta)
    one_b = 1 - beta
    log_fk = np.log(F / strikes)
    fk_pow = (F * strikes) ** (one_b / 2)
    denom = fk_pow * (1 + one_b**2 * log_fk**2 / 24 + one_b**4 * log_fk**4 / 1920)
    time0 = 1 + one_b**2 * alpha**2 * T / (24 * fk_pow**2)
    derivative = (
        alpha
        / denom
        * (-0.5 * rho * (fk_pow / alpha) * log_fk * time0 + rho * beta * alpha * T / (4 * fk_pow))
    )
    return {1: np.zeros_like(strikes), 2: derivative * SCALE[2] / noise_scale}


def _jacobian(evaluate, theta, h, analytic_columns=None):
    if not np.isfinite(h) or h <= 0 or h > np.min((UPPER - LOWER) / SCALE) / 2:
        raise ValueError("positive finite scaled step within research box required")
    columns, schemes = [], []
    for axis in range(3):
        if analytic_columns and axis in analytic_columns:
            columns.append(analytic_columns[axis])
            schemes.append("analytic_nu_zero")
            continue
        delta = np.zeros(3)
        delta[axis] = SCALE[axis] * h
        if theta[axis] - delta[axis] >= LOWER[axis] and theta[axis] + delta[axis] <= UPPER[axis]:
            column = (evaluate(theta + delta) - evaluate(theta - delta)) / (2 * h)
            scheme = "central"
        elif theta[axis] - delta[axis] < LOWER[axis]:
            column = (
                -3 * evaluate(theta) + 4 * evaluate(theta + delta) - evaluate(theta + 2 * delta)
            ) / (2 * h)
            scheme = "forward_3point"
        else:
            column = (
                3 * evaluate(theta) - 4 * evaluate(theta - delta) + evaluate(theta - 2 * delta)
            ) / (2 * h)
            scheme = "backward_3point"
        columns.append(column)
        schemes.append(scheme)
    return np.column_stack(columns), schemes


def scaled_jacobian(F, T, beta, theta, strikes, h=3e-5, noise_scale=0.0005):
    """Return d(IV/noise_scale)/du for u=theta/SCALE, shape (n_quotes,3).

    Interior coordinates use central differences in scaled u. At a research
    box boundary, a three-point inward one-sided derivative is used. Both
    schemes are second-order in h; h denotes an absolute scaled-u step.
    At exactly nu=0, rho and nu columns use analytic Hagan limits to avoid
    logarithm cancellation producing spurious singular values. This extension
    is not used at small positive nu: those numerical columns need a separate
    multi-step stability check before rank can be interpreted.
    """
    theta, strikes = _inputs(F, T, beta, theta, strikes)
    _bounded(theta)
    _noise_scale(noise_scale)
    analytic = _zero_nu_columns(F, T, beta, theta, strikes, noise_scale)
    return _jacobian(lambda p: sabr_vols(F, T, beta, p, strikes) / noise_scale, theta, h, analytic)[
        0
    ]


def jacobian_diagnostics(J, rank_rtol=1e-8):
    """Return three singular values and full right directions even for 1/2 quotes.

    ``right_vectors`` contains the rows of Vh, in descending singular-value
    order. Numerical rank uses singular values greater than rank_rtol*s_max.
    Condition is None if rank<3; a zero Jacobian has rank zero.
    """
    J = np.asarray(J, dtype=float)
    if J.ndim != 2 or J.shape[1] != 3 or not J.shape[0] or not np.isfinite(J).all():
        raise ValueError("finite nonempty Jacobian with three columns required")
    if not np.isfinite(rank_rtol) or not 0 < rank_rtol < 1:
        raise ValueError("rank_rtol must lie in (0,1)")
    _, values, right = np.linalg.svd(J, full_matrices=True)
    values = np.pad(values, (0, 3 - len(values)))
    rank = int(np.sum(values > rank_rtol * values[0]))
    return {
        "singular_values": values,
        "right_vectors": right,
        "rank": rank,
        "condition": float(values[0] / values[2]) if rank == 3 else None,
    }


def fit_smile(F, T, beta, strikes, quotes, start, fixed=None, max_nfev=400, noise_scale=0.0005):
    """Fit scaled Hagan IV residuals with bounded TRF; retain failed solver results.

    Fixed coordinates are supplied as {axis: value} in theta units, and starts
    always contain all three coordinates. Diagnostic Jacobians retain all
    three directions even during nuisance fitting. Residual call counts include
    SciPy's numerical-Jacobian calls; diagnostic IV calls are counted separately.
    ``q`` is the full residual sum of squares (twice SciPy's linear-loss cost).
    """
    start, strikes = _inputs(F, T, beta, start, strikes)
    _bounded(start)
    _noise_scale(noise_scale)
    quotes = np.asarray(quotes, dtype=float)
    if quotes.shape != strikes.shape or not np.isfinite(quotes).all() or np.any(quotes <= 0):
        raise ValueError("matching finite positive quotes required")
    if not isinstance(max_nfev, (int, np.integer)) or max_nfev < 1:
        raise ValueError("positive integer max_nfev required")
    fixed = {} if fixed is None else dict(fixed)
    effective_start = start.copy()
    for axis, value in fixed.items():
        if axis not in (0, 1, 2) or not np.isfinite(value):
            raise ValueError("fixed must map coordinate indices to finite values")
        effective_start[axis] = value
    _bounded(effective_start)
    free = np.array([axis for axis in range(3) if axis not in fixed], dtype=int)
    if not free.size:
        raise ValueError("at least one nuisance coordinate must remain free")
    residual_calls = 0
    diagnostic_calls = 0

    def restore(u):
        theta = effective_start.copy()
        theta[free] = u * SCALE[free]
        return theta

    def residual(u):
        nonlocal residual_calls
        residual_calls += 1
        return (sabr_vols(F, T, beta, restore(u), strikes) - quotes) / noise_scale

    def diagnostic(theta):
        nonlocal diagnostic_calls
        diagnostic_calls += 1
        return sabr_vols(F, T, beta, theta, strikes)

    started = perf_counter()
    result = least_squares(
        residual,
        effective_start[free] / SCALE[free],
        bounds=(LOWER[free] / SCALE[free], UPPER[free] / SCALE[free]),
        method="trf",
        jac="3-point",
        loss="linear",
        x_scale=1,
        ftol=1e-10,
        xtol=1e-10,
        gtol=1e-10,
        max_nfev=max_nfev,
    )
    solver_seconds = perf_counter() - started
    theta = restore(result.x)
    iv = diagnostic(theta)
    raw_residual = iv - quotes
    scaled_residual = raw_residual / noise_scale
    analytic = _zero_nu_columns(F, T, beta, theta, strikes, noise_scale)
    scaled_J, schemes = _jacobian(lambda p: diagnostic(p) / noise_scale, theta, 3e-5, analytic)
    theta_J = scaled_J * noise_scale / SCALE
    raw_J = theta_J / np.array([F ** (1 - beta), 1, 1])
    active_mask = np.zeros(3, dtype=int)
    active_mask[free] = result.active_mask
    boundary_lower = (theta - LOWER) / SCALE <= 1e-6
    boundary_upper = (UPPER - theta) / SCALE <= 1e-6
    seconds = perf_counter() - started
    return {
        "success": bool(result.success),
        "status": int(result.status),
        "message": str(result.message),
        "active_mask": active_mask,
        "optimality": float(result.optimality),
        "nfev": int(result.nfev),
        "njev": int(result.njev) if result.njev is not None else None,
        "residual_calls": residual_calls,
        "diagnostic_calls": diagnostic_calls,
        "scalar_iv_evaluations": int(strikes.size) * (residual_calls + diagnostic_calls),
        "seconds": seconds,
        "solver_seconds": solver_seconds,
        "diagnostic_seconds": seconds - solver_seconds,
        "start": start.copy(),
        "effective_start": effective_start,
        "theta": theta,
        "alpha": float(theta[0] * F ** (1 - beta)),
        "fixed": fixed,
        "iv": iv,
        "raw_residual": raw_residual,
        "scaled_residual": scaled_residual,
        "q": float(np.dot(scaled_residual, scaled_residual)),
        "raw_jacobian": raw_J,
        "theta_jacobian": theta_J,
        "scaled_jacobian": scaled_J,
        "jacobian_scheme": schemes,
        "jacobian_step": 3e-5,
        "noise_scale": float(noise_scale),
        "boundary_flags": boundary_lower | boundary_upper,
        "boundary_lower": boundary_lower,
        "boundary_upper": boundary_upper,
        **jacobian_diagnostics(scaled_J),
    }
