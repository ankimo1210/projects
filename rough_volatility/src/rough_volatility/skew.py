"""Local ATM implied-volatility skew and maturity-scaling regressions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from rough_volatility.estimators import loglog_ols


@dataclass(frozen=True)
class SkewEstimate:
    """Weighted local-quadratic ATM slope and diagnostics."""

    slope: float
    se: float
    n_used: int
    ok: bool
    intercept: float = float("nan")
    curvature: float = float("nan")
    r_squared: float = float("nan")
    window: float = float("nan")


@dataclass(frozen=True)
class PowerLawFit:
    """Fit of absolute ATM skew against maturity on log-log axes."""

    beta: float
    beta_se: float
    intercept: float
    r_squared: float
    h_implied: float
    n_used: int
    ok: bool


def skew_window(
    maturity: float,
    xi0: float,
    coeff: float = 1.5,
    cap: float = 0.10,
    floor: float = 0.03,
) -> float:
    """Return ``clip(coeff*sqrt(xi0*T), floor, cap)``."""
    if maturity <= 0 or xi0 <= 0 or coeff <= 0:
        raise ValueError("maturity, xi0 and coeff must be positive")
    if not 0 < floor <= cap:
        raise ValueError("window floor and cap are invalid")
    return float(np.clip(coeff * np.sqrt(xi0 * maturity), floor, cap))


def _failed_skew(n_used: int, window: float) -> SkewEstimate:
    return SkewEstimate(
        slope=float("nan"),
        se=float("nan"),
        n_used=n_used,
        ok=False,
        window=window,
    )


def atm_skew(smile: pd.DataFrame, window: float) -> SkewEstimate:
    """Estimate the ATM derivative with weighted local-quadratic regression."""
    required = {"k", "iv", "iv_se", "ok"}
    missing = required - set(smile.columns)
    if missing:
        raise ValueError(f"smile is missing columns: {sorted(missing)}")
    if window <= 0:
        raise ValueError("window must be positive")
    k = smile["k"].to_numpy(dtype=float)
    iv = smile["iv"].to_numpy(dtype=float)
    iv_se = smile["iv_se"].to_numpy(dtype=float)
    valid = (
        smile["ok"].to_numpy(dtype=bool)
        & np.isfinite(k)
        & np.isfinite(iv)
        & np.isfinite(iv_se)
        & (iv_se > 0)
        & (np.abs(k) <= window + 1e-14)
    )
    n_used = int(valid.sum())
    if n_used < 5:
        return _failed_skew(n_used, window)

    x = k[valid]
    y = iv[valid]
    weights = 1.0 / iv_se[valid] ** 2
    design = np.column_stack((np.ones(n_used), x, x**2))
    information = design.T @ (weights[:, None] * design)
    try:
        covariance = np.linalg.inv(information)
    except np.linalg.LinAlgError:
        return _failed_skew(n_used, window)
    coefficients = covariance @ (design.T @ (weights * y))
    fitted = design @ coefficients
    weighted_mean = float(np.average(y, weights=weights))
    total = float(np.sum(weights * (y - weighted_mean) ** 2))
    residual = float(np.sum(weights * (y - fitted) ** 2))
    r_squared = 1.0 if total <= np.finfo(float).eps else 1.0 - residual / total
    return SkewEstimate(
        slope=float(coefficients[1]),
        se=float(np.sqrt(max(covariance[1, 1], 0.0))),
        n_used=n_used,
        ok=True,
        intercept=float(coefficients[0]),
        curvature=float(coefficients[2]),
        r_squared=r_squared,
        window=window,
    )


def skew_term_structure(
    surface: pd.DataFrame,
    xi0: float,
    *,
    coeff: float = 1.5,
    cap: float = 0.10,
    floor: float = 0.03,
) -> pd.DataFrame:
    """Estimate one ATM skew per maturity, retaining explicit failed rows."""
    if "maturity" not in surface:
        raise ValueError("surface is missing the maturity column")
    rows: list[dict[str, float | int | bool]] = []
    for maturity, smile in surface.groupby("maturity", sort=True):
        local_window = skew_window(float(maturity), xi0, coeff, cap, floor)
        estimate = atm_skew(smile, local_window)
        rows.append(
            {
                "maturity": float(maturity),
                "skew": estimate.slope,
                "skew_se": estimate.se,
                "n_used": estimate.n_used,
                "window": local_window,
                "r_squared": estimate.r_squared,
                "ok": estimate.ok,
            }
        )
    return pd.DataFrame(rows)


def power_law_fit(term: pd.DataFrame) -> PowerLawFit:
    """Fit ``log(abs(skew)) = intercept + beta*log(maturity)``."""
    required = {"maturity", "skew", "skew_se", "ok"}
    missing = required - set(term.columns)
    if missing:
        raise ValueError(f"term structure is missing columns: {sorted(missing)}")
    maturity = term["maturity"].to_numpy(dtype=float)
    slope = term["skew"].to_numpy(dtype=float)
    slope_se = term["skew_se"].to_numpy(dtype=float)
    valid = (
        term["ok"].to_numpy(dtype=bool)
        & np.isfinite(maturity)
        & np.isfinite(slope)
        & np.isfinite(slope_se)
        & (maturity > 0)
        & (slope != 0)
        & (slope_se > 0)
    )
    n_used = int(valid.sum())
    if n_used < 3:
        return PowerLawFit(
            beta=float("nan"),
            beta_se=float("nan"),
            intercept=float("nan"),
            r_squared=float("nan"),
            h_implied=float("nan"),
            n_used=n_used,
            ok=False,
        )
    relative_precision = np.abs(slope[valid]) / slope_se[valid]
    fit = loglog_ols(maturity[valid], np.abs(slope[valid]), weights=relative_precision**2)
    return PowerLawFit(
        beta=fit.slope,
        beta_se=fit.slope_se,
        intercept=fit.intercept,
        r_squared=fit.r_squared,
        h_implied=fit.slope + 0.5,
        n_used=n_used,
        ok=True,
    )
