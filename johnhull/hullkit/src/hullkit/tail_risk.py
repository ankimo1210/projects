"""Filtered historical simulation and extreme value theory (POT/GPD) tail risk.

Shares P&L/VaR conventions with `hullkit.risk`: P&L arrays have gains
positive, VaR/ES are positive loss amounts, and `alpha` is the coverage
level (default 0.99) with exceedance probability `p = 1 - alpha`.

Filtered historical simulation (FHS) devolatilizes a return series by an
aligned conditional-volatility path (e.g. the square root of
`hullkit.volatility.ewma_variance` or `garch11_variance`), rescales the
standardized residuals to a target volatility level, and reuses
`hullkit.risk.historical_var_es`'s tail-selection convention on the
rescaled scenarios so results compose exactly with vol 08.

The peaks-over-threshold (POT) GPD fit follows the McNeil & Frey (2000)
two-step approach: fit a Generalized Pareto Distribution to threshold
exceedances by maximum likelihood, then invert the fitted tail for
closed-form VaR/ES beyond the fitting sample.

References: Barone-Adesi, Giannopoulos & Vosper (1999), *VaR without
correlations for non-linear portfolios*; McNeil & Frey (2000), *Estimation
of Tail-Related Risk Measures for Heteroscedastic Financial Time Series: an
Extreme Value Approach*; McNeil, Frey & Embrechts, *Quantitative Risk
Management*.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from . import risk

_XI_ZERO_TOL = 1e-6


def _validate_alpha(alpha: float) -> None:
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")


def _validate_positive_sigma(sigma: np.ndarray) -> None:
    if not np.all(np.isfinite(sigma)):
        raise ValueError("sigma must be finite")
    if np.any(sigma <= 0.0):
        raise ValueError("sigma must be strictly positive")


def _validate_positive_scalar_sigma(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and strictly positive, got {value}")


def _validate_finite_1d(values, name: str) -> np.ndarray:
    """Return `values` as a finite one-dimensional float array or raise ValueError."""
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got shape {arr.shape}")
    if arr.size == 0:
        raise ValueError(f"{name} must be non-empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must be finite")
    return arr


def _validate_integer_count(value, name: str) -> int:
    """Return `value` as an int, rejecting bool and non-integer counts.

    `bool` is excluded deliberately: `isinstance(True, int)` is True in Python.
    """
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be an integer, got bool {value}")
    if isinstance(value, (int, np.integer)):
        return int(value)
    raise ValueError(f"{name} must be an integer, got {type(value).__name__} {value}")


def filtered_historical_var_es(returns, sigma, alpha=0.99, current_sigma=None):
    """Filtered historical simulation (FHS) VaR/ES (Barone-Adesi et al. 1999).

    Devolatilizes `returns` by the aligned, strictly positive conditional
    volatility path `sigma` (e.g. `sqrt(ewma_variance(...))` or
    `sqrt(garch11_variance(...))`) into standardized residuals
    `z_i = returns_i / sigma_i`, rescales them to `current_sigma` (default
    `sigma[-1]`, i.e. today's level) to build FHS scenario P&Ls
    `z_i * current_sigma`, and reuses `hullkit.risk.historical_var_es`'s
    tail-selection convention on those rescaled scenarios. Returns
    `(var, es)` as positive loss amounts. Raises ValueError unless `returns`
    and `sigma` are non-empty, one-dimensional, equal-length and finite, and
    `sigma`/`current_sigma` are strictly positive. Non-finite returns are
    rejected rather than propagated: NaN sorts to the end of the scenario
    array, which would displace the tail and yield a finite but wrong VaR.
    """
    returns_arr = _validate_finite_1d(returns, "returns")
    sigma_arr = _validate_finite_1d(sigma, "sigma")
    if returns_arr.shape != sigma_arr.shape:
        raise ValueError("returns and sigma must have the same length")
    _validate_positive_sigma(sigma_arr)
    _validate_alpha(alpha)

    target_sigma = float(sigma_arr[-1]) if current_sigma is None else float(current_sigma)
    _validate_positive_scalar_sigma(target_sigma, "current_sigma")
    z = returns_arr / sigma_arr
    scenarios = z * target_sigma
    return risk.historical_var_es(scenarios, alpha=alpha)


@dataclass(frozen=True)
class GPDFit:
    """Fitted Generalized Pareto Distribution over peaks-over-threshold exceedances."""

    xi: float
    beta: float
    threshold: float
    n_exceedances: int
    n_total: int


def _gpd_neg_loglik(params, y: np.ndarray) -> float:
    xi, beta = params
    if beta <= 0.0:
        return 1e10
    n_u = y.size
    if abs(xi) < _XI_ZERO_TOL:
        # exponential limit (xi -> 0): pdf = (1/beta) exp(-y/beta)
        return float(n_u * math.log(beta) + np.sum(y) / beta)
    z = xi * y / beta
    if np.any(z <= -1.0):
        return 1e10
    return float(n_u * math.log(beta) + (1.0 + 1.0 / xi) * np.sum(np.log1p(z)))


def fit_gpd_pot(losses, threshold, min_exceedances=30):
    """Fit a GPD to peaks-over-threshold exceedances by MLE (McNeil & Frey 2000).

    Exceedances `y_i = L_i - threshold` for `L_i > threshold` (strict), out
    of `n_total = len(losses)`. Maximizes the GPD log-likelihood (`|xi| <
    1e-6` uses the numerically stable exponential-limit form) via
    Nelder-Mead, with a large penalty for `beta <= 0` or support violations
    `1 + xi*y/beta <= 0` -- same style as `hullkit.volatility.garch11_fit`.
    Raises ValueError unless `losses` is a non-empty, one-dimensional, finite
    array, `threshold` is finite and `min_exceedances` is a positive integer;
    if fewer than `min_exceedances` exceedances are found; if the optimizer
    does not converge; or if the fitted parameters are not a usable GPD
    (non-finite `xi`/`beta`, `beta <= 0`, a support violation, or a
    non-finite objective).
    """
    losses_arr = _validate_finite_1d(losses, "losses")
    threshold = float(threshold)
    if not math.isfinite(threshold):
        raise ValueError(f"threshold must be finite, got {threshold}")
    min_exceedances = _validate_integer_count(min_exceedances, "min_exceedances")
    if min_exceedances <= 0:
        raise ValueError(f"min_exceedances must be positive, got {min_exceedances}")
    y = losses_arr[losses_arr > threshold] - threshold
    n_exceedances = int(y.size)
    n_total = int(losses_arr.size)
    if n_exceedances < min_exceedances:
        raise ValueError(
            f"fit_gpd_pot requires at least {min_exceedances} exceedances above "
            f"threshold {threshold}, got {n_exceedances}"
        )

    y_mean = float(np.mean(y))
    y_var = float(np.var(y))
    if y_var > 0.0:
        # method-of-moments starting point: Mean=beta/(1-xi), Var=beta^2/((1-xi)^2(1-2xi))
        xi0 = 0.5 * (1.0 - (y_mean**2) / y_var)
        beta0 = 0.5 * y_mean * ((y_mean**2) / y_var + 1.0)
    else:
        xi0, beta0 = 0.1, max(y_mean, 1e-6)
    if not np.isfinite(xi0):
        xi0 = 0.1
    if not np.isfinite(beta0) or beta0 <= 0.0:
        beta0 = max(y_mean, 1e-6)

    res = minimize(
        _gpd_neg_loglik,
        (xi0, beta0),
        args=(y,),
        method="Nelder-Mead",
        options={"xatol": 1e-10, "fatol": 1e-8, "maxiter": 5000},
    )
    if not res.success:
        raise ValueError(f"fit_gpd_pot did not converge: {res.message}")

    xi_hat, beta_hat = (float(v) for v in res.x)
    if not (math.isfinite(xi_hat) and math.isfinite(beta_hat)):
        raise ValueError(f"fit_gpd_pot produced non-finite parameters: xi={xi_hat}, beta={beta_hat}")
    if beta_hat <= 0.0:
        raise ValueError(f"fit_gpd_pot produced a non-positive scale: beta={beta_hat}")
    if xi_hat < 0.0 and np.any(1.0 + xi_hat * y / beta_hat <= 0.0):
        raise ValueError(
            "fit_gpd_pot produced parameters that violate the GPD support "
            f"1 + xi*y/beta > 0 (xi={xi_hat}, beta={beta_hat})"
        )
    if not math.isfinite(_gpd_neg_loglik((xi_hat, beta_hat), y)):
        raise ValueError("fit_gpd_pot produced a non-finite log-likelihood at the optimum")
    return GPDFit(
        xi=xi_hat,
        beta=beta_hat,
        threshold=float(threshold),
        n_exceedances=n_exceedances,
        n_total=n_total,
    )


def evt_var_es(fit: GPDFit, alpha: float = 0.99) -> tuple[float, float]:
    """Closed-form GPD tail VaR/ES beyond a POT fit (McNeil & Frey 2000).

    `VaR = u + (beta/xi)[(n/N_u * (1-alpha))^-xi - 1]`,
    `ES = (VaR + beta - xi*u) / (1 - xi)`; `|xi| < 1e-6` uses the
    exponential-limit formulas `VaR = u + beta*ln(N_u/(n*(1-alpha)))`,
    `ES = VaR + beta`. Validates the `GPDFit` invariants before computing:
    finite `xi`/`beta`/`threshold`, `beta > 0`, integer counts with
    `0 < n_exceedances <= n_total`, and `xi < 1`. Raises ValueError on any
    violation -- including the infinite-mean regime `xi >= 1` and an implied
    VaR below the fitted threshold (alpha not extreme enough for this tail
    fit) -- rather than returning NaN or raising a bare numeric error.
    """
    _validate_alpha(alpha)
    for name in ("xi", "beta", "threshold"):
        value = getattr(fit, name)
        if not math.isfinite(value):
            raise ValueError(f"evt_var_es: fit.{name} must be finite, got {value}")
    if fit.beta <= 0.0:
        raise ValueError(f"evt_var_es: fit.beta must be strictly positive, got {fit.beta}")
    n_exceedances = _validate_integer_count(fit.n_exceedances, "fit.n_exceedances")
    n_total = _validate_integer_count(fit.n_total, "fit.n_total")
    if n_exceedances <= 0:
        raise ValueError(f"evt_var_es: fit.n_exceedances must be positive, got {n_exceedances}")
    if n_exceedances > n_total:
        raise ValueError(
            f"evt_var_es: fit.n_exceedances ({n_exceedances}) cannot exceed "
            f"fit.n_total ({n_total})"
        )
    if fit.xi >= 1.0:
        raise ValueError(
            f"evt_var_es: fit.xi >= 1 is an infinite-mean regime; VaR/ES undefined, got {fit.xi}"
        )

    p = 1.0 - alpha
    ratio = (n_total / n_exceedances) * p
    if abs(fit.xi) < _XI_ZERO_TOL:
        var = fit.threshold + fit.beta * math.log(1.0 / ratio)
        es = var + fit.beta
    else:
        var = fit.threshold + (fit.beta / fit.xi) * (ratio ** (-fit.xi) - 1.0)
        es = (var + fit.beta - fit.xi * fit.threshold) / (1.0 - fit.xi)

    if var < fit.threshold:
        raise ValueError(
            "evt_var_es: implied VaR falls below the threshold; alpha is not covered "
            "by this POT tail fit"
        )
    if not (math.isfinite(var) and math.isfinite(es)):
        raise ValueError(f"evt_var_es produced non-finite output: var={var}, es={es}")
    return float(var), float(es)


def mean_excess(losses, thresholds):
    """Empirical mean excess function `e(u) = mean(L - u | L > u)` (POT diagnostic).

    Vectorized over `thresholds`; returns `np.nan` at any threshold with no
    exceedances. Plotted against `u`, a near-linear `e(u)` with slope
    `xi/(1-xi)` supports a POT threshold choice and an approximate GPD
    shape (McNeil, Frey & Embrechts, *Quantitative Risk Management*).
    """
    losses_arr = np.asarray(losses, dtype=float)
    thresholds_arr = np.asarray(thresholds, dtype=float)
    result = np.empty_like(thresholds_arr, dtype=float)
    for i, u in enumerate(thresholds_arr):
        exceed = losses_arr[losses_arr > u] - u
        result[i] = float(exceed.mean()) if exceed.size > 0 else float("nan")
    return result
