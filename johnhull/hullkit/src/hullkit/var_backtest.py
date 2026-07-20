"""VaR backtesting statistics: Kupiec POF, Christoffersen tests, Basel traffic light.

Shares P&L/VaR conventions with `hullkit.risk`: P&L arrays have gains positive,
VaR is a positive loss amount, and `alpha` is the coverage level (default
0.99) with exceedance probability `p = 1 - alpha`. An exceedance on day i
means `-pnl[i] > var_forecast[i]` (strict inequality).

References: Kupiec (1995); Christoffersen (1998); BCBS (1996) Supervisory
Framework for backtesting.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import xlogy
from scipy.stats import binom, chi2

_YELLOW_MULTIPLIER = {5: 3.40, 6: 3.50, 7: 3.65, 8: 3.75, 9: 3.85}


def _validate_alpha(alpha: float) -> None:
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")


def _validate_integer_count(value, name: str) -> int:
    """Return `value` as an int, rejecting bool, fractional and non-finite counts.

    `bool` is excluded deliberately: `isinstance(True, int)` is True in Python,
    so an unguarded count would treat `True` as one exceedance.
    """
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be an integer, got bool {value}")
    if isinstance(value, (int, np.integer)):
        return int(value)
    raise ValueError(f"{name} must be an integer, got {type(value).__name__} {value}")


def _validate_counts(n_exceedances: int, n_obs: int) -> None:
    n_exceedances = _validate_integer_count(n_exceedances, "n_exceedances")
    n_obs = _validate_integer_count(n_obs, "n_obs")
    if n_obs <= 0:
        raise ValueError(f"n_obs must be positive, got {n_obs}")
    if n_exceedances < 0:
        raise ValueError(f"n_exceedances must be non-negative, got {n_exceedances}")
    if n_exceedances > n_obs:
        raise ValueError("n_exceedances cannot exceed n_obs")


def _validate_binary_exceedances(exceedances) -> np.ndarray:
    """Cast `exceedances` to a 0/1 int array, raising ValueError otherwise.

    Guards against exceedance *counts* or *probabilities* being passed where
    a 0/1 indicator series is required -- an int cast of those would
    silently truncate instead of raising.
    """
    exc = np.asarray(exceedances, dtype=float)
    if exc.ndim != 1:
        raise ValueError(f"exceedances must be one-dimensional, got shape {exc.shape}")
    if not np.all(np.isfinite(exc)):
        raise ValueError(f"exceedances must be finite, got {exc.tolist()}")
    bad_mask = ~np.isin(exc, (0.0, 1.0))
    if np.any(bad_mask):
        bad_values = np.unique(exc[bad_mask]).tolist()
        raise ValueError(
            f"exceedances must be a binary 0/1 series, got non-binary values {bad_values}"
        )
    return exc.astype(int)


def exceedance_series(pnl, var_forecasts) -> np.ndarray:
    """Daily 0/1 exceedance indicator: 1 where `-pnl[i] > var_forecast[i]` (strict).

    `pnl` and `var_forecasts` are equal-length, one-dimensional, gains-positive
    P&L and non-negative VaR-forecast arrays. Raises ValueError on a length
    mismatch, empty or multi-dimensional input, a non-finite element, or a
    negative VaR forecast. Non-finite elements are rejected rather than
    compared, because a missing P&L or VaR would otherwise be silently
    classified as a non-exceedance. A zero forecast is allowed: it marks a
    zero-risk day, on which any loss is an exceedance.
    """
    pnl_arr = np.asarray(pnl, dtype=float)
    var_arr = np.asarray(var_forecasts, dtype=float)
    if pnl_arr.ndim != 1 or var_arr.ndim != 1:
        raise ValueError(
            "pnl and var_forecasts must be one-dimensional, got shapes "
            f"{pnl_arr.shape} and {var_arr.shape}"
        )
    if pnl_arr.shape != var_arr.shape:
        raise ValueError("pnl and var_forecasts must have the same length")
    if pnl_arr.size == 0:
        raise ValueError("exceedance_series requires non-empty pnl/var_forecasts")
    if not np.all(np.isfinite(pnl_arr)):
        raise ValueError("pnl must be finite; a missing P&L cannot be classified")
    if not np.all(np.isfinite(var_arr)):
        raise ValueError("var_forecasts must be finite; a missing VaR cannot be classified")
    if np.any(var_arr < 0.0):
        raise ValueError(
            f"var_forecasts must be non-negative, got minimum {float(var_arr.min())}"
        )
    return (-pnl_arr > var_arr).astype(int)


def kupiec_pof(n_exceedances: int, n_obs: int, alpha: float = 0.99) -> tuple[float, float]:
    """Kupiec (1995) proportion-of-failures likelihood-ratio test.

    LR_pof = -2 ln[ (1-p)^(n-x) p^x / (1-pi_hat)^(n-x) pi_hat^x ], pi_hat = x/n,
    p = 1 - alpha, with the convention 0*ln(0) = 0. Returns
    `(lr_stat, p_value)` where p_value is `scipy.stats.chi2.sf(lr_stat, df=1)`.
    Uses the full sample; see `christoffersen_cc` for the transition-conditioned
    variant used in the conditional-coverage decomposition.
    """
    _validate_alpha(alpha)
    _validate_counts(n_exceedances, n_obs)
    n = float(n_obs)
    x = float(n_exceedances)
    p = 1.0 - alpha
    pi_hat = x / n
    log_num = xlogy(n - x, 1.0 - p) + xlogy(x, p)
    log_den = xlogy(n - x, 1.0 - pi_hat) + xlogy(x, pi_hat)
    lr = -2.0 * (log_num - log_den)
    p_value = float(chi2.sf(lr, df=1))
    return float(lr), p_value


def christoffersen_independence(exceedances) -> tuple[float, float]:
    """Christoffersen (1998) independence likelihood-ratio test.

    Counts transitions n00, n01, n10, n11 over the n-1 consecutive pairs of a
    0/1 exceedance series and compares the restricted model (constant
    exceedance probability `pi_bar`) against the unrestricted 2-state Markov
    model. Returns `(lr_stat, p_value)` with `p_value = chi2.sf(lr_stat, df=1)`.
    Raises ValueError if fewer than 2 observations are given, or if any
    element of `exceedances` is not exactly 0 or 1 (e.g. exceedance counts
    or probabilities passed by mistake). A degenerate all-zero or all-one
    series returns `(0.0, 1.0)` (no transitions to test).
    """
    exc = _validate_binary_exceedances(exceedances)
    if exc.size < 2:
        raise ValueError("christoffersen_independence requires at least 2 observations")
    if np.unique(exc).size == 1:
        return 0.0, 1.0

    prev, curr = exc[:-1], exc[1:]
    n00 = int(np.sum((prev == 0) & (curr == 0)))
    n01 = int(np.sum((prev == 0) & (curr == 1)))
    n10 = int(np.sum((prev == 1) & (curr == 0)))
    n11 = int(np.sum((prev == 1) & (curr == 1)))
    n_trans = n00 + n01 + n10 + n11

    pi01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    pi11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0
    pi_bar = (n01 + n11) / n_trans

    log_num = xlogy(n00 + n10, 1.0 - pi_bar) + xlogy(n01 + n11, pi_bar)
    log_den = (
        xlogy(n00, 1.0 - pi01)
        + xlogy(n01, pi01)
        + xlogy(n10, 1.0 - pi11)
        + xlogy(n11, pi11)
    )
    lr = -2.0 * (log_num - log_den)
    p_value = float(chi2.sf(lr, df=1))
    return float(lr), p_value


def christoffersen_cc(exceedances, alpha: float = 0.99) -> tuple[float, float]:
    """Christoffersen (1998) conditional-coverage likelihood-ratio test.

    `LR_cc = LR_pof^(n-1) + LR_ind ~ chi2(2)`, where `LR_pof^(n-1)` is
    `kupiec_pof` evaluated on the transition-conditioned sample (the n-1
    observations `exceedances[1:]`) so the sum is an exact identity with
    `christoffersen_independence`. Returns `(lr_stat, p_value)` with
    `p_value = chi2.sf(lr_stat, df=2)`. Raises ValueError if any element of
    `exceedances` is not exactly 0 or 1, same as `christoffersen_independence`.
    """
    _validate_alpha(alpha)
    exc = _validate_binary_exceedances(exceedances)
    lr_ind, _ = christoffersen_independence(exc)
    n = exc.size
    x_trans = int(exc[1:].sum())
    lr_pof_trans, _ = kupiec_pof(x_trans, n - 1, alpha=alpha)
    lr_cc = lr_pof_trans + lr_ind
    p_value = float(chi2.sf(lr_cc, df=2))
    return float(lr_cc), p_value


@dataclass(frozen=True)
class BaselZone:
    """Basel traffic-light classification: zone, cumulative probability, multiplier."""

    zone: str
    cumulative_probability: float
    multiplier: float


def basel_traffic_light(n_exceedances: int, n_obs: int = 250, alpha: float = 0.99) -> BaselZone:
    """BCBS (1996) traffic-light zone and capital multiplier add-on.

    Zone from the binomial cumulative probability `P(X <= x)`, `X ~ B(n, p)`,
    `p = 1 - alpha`: green `< 0.95`, yellow `[0.95, 0.9999)`, red `>= 0.9999`.
    At `n=250, p=0.01` this reproduces green x<=4, yellow 5<=x<=9, red x>=10.
    Multiplier: green 3.00; yellow 3.40/3.50/3.65/3.75/3.85 for x=5..9 (clamped
    to that range for yellow zones outside it); red 4.00. The count-keyed
    yellow multiplier table is the 250-day BCBS schedule and is only
    documented (not re-derived) when `n_obs != 250`.
    """
    _validate_alpha(alpha)
    _validate_counts(n_exceedances, n_obs)
    p = 1.0 - alpha
    cumulative_probability = float(binom.cdf(n_exceedances, n_obs, p))

    if cumulative_probability < 0.95:
        zone = "green"
        multiplier = 3.00
    elif cumulative_probability < 0.9999:
        zone = "yellow"
        clamped_x = min(9, max(5, n_exceedances))
        multiplier = _YELLOW_MULTIPLIER[clamped_x]
    else:
        zone = "red"
        multiplier = 4.00

    return BaselZone(zone=zone, cumulative_probability=cumulative_probability, multiplier=multiplier)
